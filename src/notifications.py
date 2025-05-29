# src/notifications.py
import logging
from typing import Optional
from .config import get_settings
from .models import BookingRequest

settings = get_settings()
logger = logging.getLogger(__name__)

def send_sms_alert(message: str) -> bool:
    """Send SMS alert using Twilio"""
    if not all([settings.twilio_account_sid, settings.twilio_auth_token, 
                settings.twilio_phone_number, settings.alert_phone_number]):
        logger.warning("Twilio credentials not configured, skipping SMS")
        return False
    
    try:
        from twilio.rest import Client
        
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        message = client.messages.create(
            body=message,
            from_=settings.twilio_phone_number,
            to=settings.alert_phone_number
        )
        
        logger.info(f"SMS sent successfully: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS: {str(e)}")
        return False

def send_email_alert(subject: str, message: str) -> bool:
    """Send email alert using SendGrid"""
    if not all([settings.sendgrid_api_key, settings.alert_email, settings.from_email]):
        logger.warning("SendGrid credentials not configured, skipping email")
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        mail = Mail(
            from_email=settings.from_email,
            to_emails=settings.alert_email,
            subject=subject,
            html_content=f"<p>{message}</p>"
        )
        
        sg = SendGridAPIClient(api_key=settings.sendgrid_api_key)
        response = sg.send(mail)
        
        logger.info(f"Email sent successfully: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_booking_notification(booking_request: BookingRequest, success: bool, 
                            error: Optional[str] = None):
    """Send notification about booking result"""
    date_str = booking_request.requested_date.strftime('%Y-%m-%d')
    time_str = booking_request.requested_time.strftime('%I:%M %p')
    
    if success:
        subject = f"Golf Booking Successful - {date_str}"
        message = f"Successfully booked tee time for {booking_request.user_name} on {date_str} at {time_str}"
        logger.info(message)
        
        # Send success email
        send_email_alert(subject, message)
        
    else:
        subject = f"Golf Booking Failed - {date_str}"
        message = f"Failed to book tee time for {booking_request.user_name} on {date_str} at {time_str}"
        
        if error:
            message += f"\nError: {error}"
        
        logger.error(message)
        
        # Send failure notifications (both email and SMS for failures)
        send_email_alert(subject, message)
        send_sms_alert(f"Golf booking failed for {date_str} at {time_str}. Check email for details.")

def send_site_down_alert():
    """Send alert when golf site is down"""
    message = "Golf club website appears to be down. Booking attempts will continue with retries."
    logger.warning(message)
    
    send_email_alert("Golf Site Down Alert", message)
    send_sms_alert("Golf site down - booking retries in progress")