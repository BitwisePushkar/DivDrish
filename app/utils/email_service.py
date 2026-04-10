"""
Email service for the DeepTrace ML Engine.

Handles sending OTPs and security alerts.
"""
from flask import current_app
from flask_mailman import EmailMessage
from app.utils.logger import logger


def send_otp_email(email: str, otp: str, purpose: str = "registration"):
    """
    Send a 6-digit OTP to the specified email address.
    
    Args:
        email: Recipient email address.
        otp: 6-digit code.
        purpose: 'registration' or 'password_reset'.
    """
    subjects = {
        "registration": f"Verify your registration for {current_app.config.get('APP_NAME')}",
        "password_reset": f"Password reset OTP for {current_app.config.get('APP_NAME')}",
    }
    
    subject = subjects.get(purpose, "Security Verification Code")
    body = f"""
    Your verification code is: {otp}
    
    This code will expire in 10 minutes. 
    If you did not request this, please ignore this email.
    
    Sent by {current_app.config.get('APP_NAME')}
    """
    
    try:
        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=current_app.config.get("DEFAULT_FROM_EMAIL"),
            to=[email]
        )
        msg.send()
        logger.info(f"OTP email sent to {email} ({purpose})")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        return False
