from celery import Celery
from app.core.config import settings

celery = Celery(
    "mhike_school",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
