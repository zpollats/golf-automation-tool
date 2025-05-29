# src/scheduler.py
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta
import os
from .config import get_settings

settings = get_settings()

# Create Celery app
celery = Celery(
    'golf_booking',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['src.scheduler']
)

# Celery configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'check-pending-bookings': {
            'task': 'src.scheduler.check_pending_bookings',
            'schedule': crontab(minute='*/5'),  # Check every 5 minutes
        },
    },
)

@celery.task(bind=True, max_retries=3)
def book_tee_time_task(self, booking_request_id: int):
    """Celery task to book a tee time"""
    from .scraper import GolfBookingScraper
    from .models import get_booking_request, update_booking_status
    from .notifications import send_booking_notification
    
    try:
        # Get booking request from database
        booking_request = get_booking_request(booking_request_id)
        if not booking_request:
            raise Exception(f"Booking request {booking_request_id} not found")
        
        # Initialize scraper
        scraper = GolfBookingScraper(
            username=settings.golf_username,
            password=settings.golf_password,
            base_url=settings.golf_club_url
        )
        
        # Attempt booking
        success = scraper.attempt_booking(
            target_date=booking_request.requested_date,
            target_time=booking_request.requested_time.strftime('%I:%M %p')
        )
        
        if success:
            # Update database with success
            update_booking_status(booking_request_id, 'completed', success=True)
            send_booking_notification(booking_request, success=True)
            return f"Successfully booked tee time for {booking_request.requested_date}"
        else:
            # Retry logic
            if self.request.retries < self.max_retries:
                # Retry in 5 minutes
                raise self.retry(countdown=300)
            else:
                # Max retries reached
                update_booking_status(booking_request_id, 'failed', success=False)
                send_booking_notification(booking_request, success=False, 
                                        error="Max booking attempts exceeded")
                return f"Failed to book tee time after {self.max_retries} attempts"
                
    except Exception as exc:
        update_booking_status(booking_request_id, 'error', success=False, error=str(exc))
        send_booking_notification(booking_request, success=False, error=str(exc))
        raise

@celery.task
def check_pending_bookings():
    """Check for bookings that should be executed now"""
    from .models import get_pending_bookings
    
    current_time = datetime.utcnow()
    pending_bookings = get_pending_bookings(current_time)
    
    for booking in pending_bookings:
        # Schedule the booking task
        book_tee_time_task.delay(booking.id)
    
    return f"Scheduled {len(pending_bookings)} booking tasks"

@celery.task
def schedule_booking(user_name: str, requested_date: str, requested_time: str):
    """Schedule a new booking request"""
    from .models import create_booking_request
    from datetime import datetime
    
    # Parse the requested date
    target_date = datetime.strptime(requested_date, '%Y-%m-%d').date()
    target_time = datetime.strptime(requested_time, '%H:%M').time()
    
    # Calculate when to execute (7 days prior at midnight)
    execution_time = datetime.combine(target_date - timedelta(days=7), 
                                    datetime.min.time())
    
    # Create booking request in database
    booking_id = create_booking_request(
        user_name=user_name,
        requested_date=target_date,
        requested_time=target_time,
        scheduled_for=execution_time
    )
    
    return f"Scheduled booking request {booking_id} for execution at {execution_time}"