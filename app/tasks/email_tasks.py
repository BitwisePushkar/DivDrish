"""
Asynchronous email tasks using Celery.
"""
from app.extensions import celery
from app.utils.email_service import send_otp_email
from app.utils.logger import logger

@celery.task(name="tasks.email.send_otp", bind=True, max_retries=3)
def send_otp_email_task(self, email, otp, purpose):
    """
    Celery task to send OTP emails asynchronously.
    """
    # Import here to avoid circular dependencies
    from wsgi import app
    
    try:
        with app.app_context():
            success = send_otp_email(email, otp, purpose)
            if not success:
                raise Exception("Email service returned False")
            return True
    except Exception as exc:
        logger.warning(f"Retrying email task for {email} due to: {exc}")
        raise self.retry(exc=exc, countdown=60)
