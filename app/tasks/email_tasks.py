from app.extensions import celery
from app.utils.logger import logger
from app.utils.email_service import send_otp_email

@celery.task(name="tasks.email.send_otp", bind=True, max_retries=3)
def send_otp_email_task(self, email, otp, purpose):
    try:
        success = send_otp_email(email, otp, purpose)
        if not success:
            raise Exception("Email service returned False")
        logger.info(f"OTP email sent to {email} for {purpose}")
        return True
    except Exception as exc:
        logger.warning(f"Retrying email task for {email} due to: {exc}")
        raise self.retry(exc=exc, countdown=60)