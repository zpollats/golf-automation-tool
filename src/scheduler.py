# src/scheduler.py
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta
import os
import logging
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
            'schedule': crontab(minute='*/10'),  # Check every 10 minutes
        },
        'start-precision-booking': {
            'task': 'src.scheduler.start_precision_booking',
            'schedule': crontab(minute=59, hour=5),  
        }
    },
)

@celery.task(bind=True, max_retries=3)
def book_tee_time_task(self, booking_request_id: int):
    """Celery task to book a tee time using Jeremy Ranch scraper"""
    logger = logging.getLogger(__name__)
    logger.info(f"🎯 Starting booking task for request ID: {booking_request_id}")
    
    try:
        # Get booking request from database
        from .models import get_booking_request, update_booking_status
        
        booking_request = get_booking_request(booking_request_id)
        if not booking_request:
            raise Exception(f"Booking request {booking_request_id} not found")
        
        logger.info(f"📋 Booking details: {booking_request.user_name} - {booking_request.requested_date} at {booking_request.requested_time}")
        
        # Update status to running
        update_booking_status(booking_request_id, 'running', success=None)
        
        # Import Jeremy Ranch scraper
        from .scraper import JeremyRanchScraper
        
        # Initialize scraper (no arguments - gets config from settings)
        scraper = JeremyRanchScraper()
        
        # Attempt booking - use test_mode=True for testing, False for real booking
        test_mode = False  # Change to False when ready for real bookings
        
        success = scraper.book_tee_time(
            target_date=booking_request.requested_date,
            preferred_time=booking_request.requested_time.strftime('%H:%M'),
            test_mode=test_mode
        )
        
        if success:
            # Update database with success
            status = 'test_success' if test_mode else 'completed'
            update_booking_status(booking_request_id, status, success=True)
            
            message = f"{'Test successful' if test_mode else 'Successfully booked'} tee time for {booking_request.requested_date}"
            logger.info(f"✅ {message}")
            
            return message
        else:
            # Retry logic
            if self.request.retries < self.max_retries:
                logger.warning(f"⚠️ Booking attempt failed, retrying in 5 minutes (attempt {self.request.retries + 1}/{self.max_retries})")
                raise self.retry(countdown=300)
            else:
                # Max retries reached
                error_msg = f"Max booking attempts exceeded ({self.max_retries} attempts)"
                logger.error(f"❌ {error_msg}")
                update_booking_status(booking_request_id, 'failed', success=False, error=error_msg)
                return f"Failed to book tee time after {self.max_retries} attempts"
                
    except Exception as exc:
        error_msg = f"Booking task error: {str(exc)}"
        logger.error(f"❌ {error_msg}")
        
        from .models import update_booking_status
        update_booking_status(booking_request_id, 'error', success=False, error=error_msg)
        
        # Don't retry on certain errors
        if "not found" in str(exc).lower() or "invalid" in str(exc).lower():
            return error_msg
        
        raise

@celery.task
def check_pending_bookings():
    """Check for bookings that should be executed now"""
    from .models import get_pending_bookings
    
    current_time = datetime.utcnow()
    pending_bookings = get_pending_bookings(current_time)
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Checking for pending bookings at {current_time}")
    logger.info(f"📋 Found {len(pending_bookings)} pending booking(s)")
    
    for booking in pending_bookings:
        logger.info(f"🚀 Scheduling booking task for: {booking.user_name} - {booking.requested_date} at {booking.requested_time}")
        # Schedule the booking task
        book_tee_time_task.delay(booking.id)
    
    return f"Scheduled {len(pending_bookings)} booking tasks"

@celery.task
def start_precision_booking():
    """Enable precision booking for the next 3 minutes"""
    import redis
    logger = logging.getLogger(__name__)

    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.setex('precision_booking_enabled', 120, 'true')
        logger.info("STARTING PRECISION BOOKING WINDOW (2 minutes)")

        precision_booking_check.delay()

        return "Precision booking enabled for 2 minutes"

    except Exception as e:
        logger.error(f"Error starting precision booking: {str(e)}")
        return f"Error starting precision booking: {str(e)}"

@celery.task
def precision_booking_check():
    """High-precision check during booking windows"""
    import redis
    from .models import get_pending_bookings
    import pytz

    logger = logging.getLogger(__name__)
    
    try:
        redis_client = redis.from_url(settings.redis_url)
        precision_enabled = redis_client.get('precision_booking_enabled')

        if not precision_enabled:
            logger.info("Precision booking window expired - stopping checks")
            return "Precision booking disabled (timeout expired)"
        
        mtn_tz = pytz.timezone('MST')
        current_mtn = datetime.now(mtn_tz)
        current_utc = current_mtn.astimezone(pytz.UTC).replace(tzinfo=None)

        logger.info(f"🔍 Checking for pending bookings at {current_mtn.strftime('%H:%M:%S')} MST")

        pending_bookings = get_pending_bookings(current_utc)
        executed_count = 0

        for booking in pending_bookings:
            time_until_execution = (booking.scheduled_for - current_utc).total_seconds()
            if time_until_execution <= 10:
                logger.info(f"EXECUTING NOW: {booking.user_name} - {booking.requested_date}")
                book_tee_time_task.delay(booking.id)
                executed_count += 1

        precision_booking_check.apply_async(countdown=3)

        return f"Precision check: {executed_count}/{len(pending_bookings)} bookings executed"
    
    except Exception as e:
        logger.error(f"Precision booking check error - {str(e)}")
        return f"Precision booking check error: {str(e)}"

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