from celery import Celery

from app.core.config import settings
from app.imports.bootstrap import register_import_handlers

register_import_handlers()


celery = Celery(
    "mhike_school",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.notifications",
        "app.tasks.imports",
        "app.tasks.assessment_publication",
    ],
)


celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "publish-due-assessment-results": {
            "task": "assessments.publish_due_scheduled_results",
            "schedule": 60.0,
        },
    },
)
