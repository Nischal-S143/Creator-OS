from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery("creatoros", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
)


@celery_app.task(name="system.ping")
def ping() -> str:
    return "pong"
