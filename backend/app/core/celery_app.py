from celery import Celery
from .config import settings

celery_app = Celery(
    "docgenie",
    broker=settings.redis_url,
    backend=settings.redis_url,
    task_serializer="json",
    result_serializer="json",
)
celery_app.conf.update(task_track_started=True)
