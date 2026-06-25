from celery import Celery
from app.core.config import settings

celery_app = Celery("sci_research_platform")

celery_app.config_from_object({
    "broker_url": settings.CELERY_BROKER_URL,
    "result_backend": settings.CELERY_RESULT_BACKEND,
    "task_serializer": settings.CELERY_TASK_SERIALIZER,
    "result_serializer": "json",
    "accept_content": ["json"],
    "worker_concurrency": settings.CELERY_WORKER_CONCURRENCY,
    "worker_prefetch_multiplier": 1,
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "task_routes": {
        "tasks.run_research_pipeline": {"queue": "pipeline"},
    },
    "beat_schedule": {},
})

celery_app.autodiscover_tasks(["app.tasks"])
