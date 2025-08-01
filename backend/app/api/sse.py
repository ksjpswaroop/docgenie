from fastapi import APIRouter, Request
from fastapi.responses import EventSourceResponse
import redis.asyncio as aioredis
from ..core.config import settings
import json, asyncio

router = APIRouter(prefix="/stream")

redis = aioredis.from_url(settings.redis_url, decode_responses=True)

@router.get("/{job_id}")
async def stream_job(job_id: str):
    async def event_generator():
        pubsub = redis.pubsub()
        await pubsub.subscribe(job_id)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {"event": "update", "data": message["data"]}
        finally:
            await pubsub.close()
    return EventSourceResponse(event_generator())
