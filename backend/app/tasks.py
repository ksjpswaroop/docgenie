from .core.celery_app import celery_app
from .core.llm import chat_stream
from .core.config import settings
from .db.database import AsyncSession, async_sessionmaker, engine
from .db.models import Job, JobStatus
from .core.templates import list_placeholders
import jinja2, json, asyncio, redis.asyncio as aioredis

# initialize redis and DB session maker
redis = aioredis.from_url(settings.redis_url, decode_responses=True)
SessionMaker = async_sessionmaker(engine, expire_on_commit=False)
template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(settings.templates_path))


def publish(job_id: str, payload: dict):
    """
    Publish a JSON payload to the Redis channel named after the job ID.
    """
    asyncio.run(redis.publish(job_id, json.dumps(payload)))


@celery_app.task
def create_outline(job_id: str):
    """Celery task entrypoint for creating an outline."""
    asyncio.run(_create_outline(job_id))


async def _create_outline(job_id: str):
    """
    Create a markdown outline for a given job.
    Loads the template, renders it with the provided answers, and streams
    the outline via Redis updates.
    """
    async with SessionMaker() as db:
        job: Job = await db.get(Job, job_id)
        if not job:
            return
        # update status and publish phase change
        job.status = JobStatus.OUTLINING
        await db.commit()
        publish(job_id, {"phase": "OUTLINING"})

        # render template into full markdown prompt
        tmpl = template_env.get_template(f"{job.template}.md")
        merged = tmpl.render(**job.answers)

        # ask LLM to produce an outline
        system_msg = {"role": "system", "content": "Return only a Markdown outline."}
        user_msg = {"role": "user", "content": merged}

        outline = ""
        async for delta in chat_stream([system_msg, user_msg], temperature=0.3):
            outline += delta
            publish(job_id, {"phase": "OUTLINING", "delta": delta})

        job.outline_md = outline
        await db.commit()
        publish(job_id, {"phase": "OUTLINE_DONE"})

        # create tasks for each H1 section
        ids = [str(i + 1) for i in range(outline.count("# "))]
        for h in ids:
            draft_section.delay(job_id, h)


@celery_app.task(bind=True, autoretry_for=(Exception,), max_retries=3)
def draft_section(self, job_id: str, h1_id: str):
    """Celery task entrypoint for drafting a single section."""
    asyncio.run(_draft_section(job_id, h1_id))


async def _draft_section(job_id: str, h1_id: str):
    """
    Draft a single H1 section based on the outline and previous sections.
    Generates both the section text and a short summary.
    """
    async with SessionMaker() as db:
        job: Job = await db.get(Job, job_id)
        # transition to DRAFTING if not already
        if job.status != JobStatus.DRAFTING:
            job.status = JobStatus.DRAFTING
            await db.commit()
        # build context for this section
        context = {
            "answers": job.answers,
            "outline": job.outline_md,
            "previous": {k: v["summary"] for k, v in job.section_map.items() if int(k) < int(h1_id)},
        }
        system_msg = {
            "role": "system",
            "content": "Write only the requested section in Markdown.",
        }
        user_msg = {
            "role": "user",
            "content": json.dumps({"context": context, "section": h1_id}),
        }

        text = ""
        async for delta in chat_stream([system_msg, user_msg], temperature=0.4):
            text += delta
            publish(job_id, {"phase": "SECTION", "section": h1_id, "delta": delta})

        # summarize the section quickly
        summary_sys = {
            "role": "system",
            "content": "Summarize the section in ≤50 words",
        }
        summary_chunks: list[str] = []
        async for d in chat_stream([summary_sys, {"role": "user", "content": text}], temperature=0.2):
            summary_chunks.append(d)
        summary = "".join(summary_chunks)

        job.section_map[h1_id] = {"text": text, "summary": summary}
        await db.commit()
        publish(job_id, {"phase": "SECTION_DONE", "section": h1_id})

        # once all sections are drafted, trigger refinement
        if len(job.section_map) == job.outline_md.count("# "):
            refine_full_doc.delay(job_id)


@celery_app.task
def refine_full_doc(job_id: str):
    """Celery task entrypoint for refining the full document."""
    asyncio.run(_refine_full_doc(job_id))


async def _refine_full_doc(job_id: str):
    """
    Combine all section texts, ask the LLM to polish the entire draft,
    and update the job status to DONE.
    """
    async with SessionMaker() as db:
        job: Job = await db.get(Job, job_id)
        job.status = JobStatus.REFINING
        await db.commit()
        publish(job_id, {"phase": "REFINING"})

        # assemble full document by H1 order
        full = "\n\n".join(
            v["text"] for _, v in sorted(job.section_map.items(), key=lambda kv: int(kv[0]))
        )
        user_msg = {"role": "user", "content": full}
        system_msg = {
            "role": "system",
            "content": "Polish the draft, fix style, return final Markdown document.",
        }

        polished = ""
        async for delta in chat_stream([system_msg, user_msg], temperature=0.25):
            polished += delta
            publish(job_id, {"phase": "REFINING", "delta": delta})

        job.final_md = polished
        job.status = JobStatus.DONE
        await db.commit()
        publish(job_id, {"phase": "DONE"})
