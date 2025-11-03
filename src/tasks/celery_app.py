"""Celery application configuration."""
from celery import Celery
from src.config import Config

celery_app = Celery(
    "fynorra_rag",
    broker=Config.REDIS_URL,
    backend=Config.REDIS_URL,
    include=["src.tasks.ingest_job", "src.tasks.worker_upsert_pinecone"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

