from app.tasks.celery_app import celery


@celery.task(name="send_welcome_email")
def send_welcome_email(email: str) -> dict:
    print(f"[EMAIL] Welcome to Mhike School -> {email}")
    return {"sent": True, "email": email}
