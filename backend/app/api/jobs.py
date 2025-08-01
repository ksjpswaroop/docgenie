from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import AsyncSession as DB
from ..db.models import Job, JobStatus
from ..core.templates import list_placeholders
from ..tasks import create_outline
import uuid

router = APIRouter(prefix="/jobs")

async def get_db():
    async with DB() as session:
        yield session

@router.post("/", status_code=202)
async def create_job(payload: dict, db: AsyncSession = Depends(get_db), user_id: str = Depends(...)):
    template = payload["template"]
    answers = payload["answers"]

    placeholders = list_placeholders(template)
    missing = [ph for ph in placeholders if ph not in answers]

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        user_id=user_id,
        template=template,
        answers=answers,
        status=JobStatus.AWAITING_INPUT if missing else JobStatus.QUEUED,
    )
    db.add(job)
    await db.commit()

    if not missing:
        create_outline.delay(job_id)

    return {"job_id": job_id, "missing": missing}

@router.patch("/{job_id}/answers", status_code=202)
async def patch_answers(
    job_id: str,
    new: dict,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(...),
):
    q = await db.get(Job, job_id)
    if not q or q.user_id != user_id:
        raise HTTPException(404)
    q.answers.update(new)
    # re-compute missing
    missing = [ph for ph in list_placeholders(q.template) if ph not in q.answers]
    q.status = JobStatus.AWAITING_INPUT if missing else JobStatus.QUEUED
    await db.commit()
    if not missing:
        create_outline.delay(job_id)
    return {"missing": missing}
