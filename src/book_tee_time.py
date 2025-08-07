import sys
import os
from datetime import datetime, date, time, timedelta, timezone
import pytz

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models import create_booking_request
from src.scheduler import schedule_booking

def main():
    """Simple CLI for booking tee times"""
    
    print("🏌️  Golf Booking Automation - CLI")
    print("=" * 50)
    
    # Get user input
    try:
        user_name = input("Enter your name: ").strip()
        if not user_name:
            print("❌ Name cannot be empty")
            return
        
        # Get date
        date_input = input("Enter date (YYYY-MM-DD, e.g., 2025-06-20): ").strip()
        try:
            requested_date = datetime.strptime(date_input, '%Y-%m-%d').date()
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return
        
        # Validate date is in future
        utc_now = datetime.now(timezone.utc)
        local_now = utc_now - timedelta(hours=6)
        today = local_now.date()
        if requested_date <= today:
            print("❌ Date must be in the future")
            return
        
        # Check if this is within 7 days (immediate booking) or future scheduling
        days_out = (requested_date - today).days
        is_immediate_booking = days_out <= 7
        
        if is_immediate_booking:
            print(f"🚀 This date is {days_out} days away - will book IMMEDIATELY!")
            execution_datetime_utc = datetime.utcnow()  # Book right now
        else:
            # Future booking - schedule for 7 days prior
            if days_out <= 7:
                print("❌ Date must be more than 7 days in the future for scheduled booking")
                print(f"   (Earliest allowed: {(today + timedelta(days=8)).strftime('%Y-%m-%d')})")
                return
        
        # Get time
        time_input = input("Enter preferred time (HH:MM, e.g., 08:00): ").strip()
        try:
            requested_time = datetime.strptime(time_input, '%H:%M').time()
        except ValueError:
            print("❌ Invalid time format. Use HH:MM (24-hour format)")
            return
        
        # Validate reasonable golf hours
        if requested_time < time(6, 0) or requested_time > time(18, 0):
            print("❌ Time must be between 06:00 and 18:00")
            return
        
        print(f"\n📋 Booking Summary:")
        print(f"   Name: {user_name}")
        print(f"   Date: {requested_date.strftime('%A, %B %d, %Y')} ({days_out} days away)")
        print(f"   Time: {requested_time.strftime('%I:%M %p')}")
        
        if is_immediate_booking:
            print(f"   🚀 IMMEDIATE BOOKING - Will execute within minutes!")
            execution_time_display = "ASAP (within 5 minutes)"
        else:
            # Calculate execution time for future bookings
            execution_date = requested_date - timedelta(days=7)
            execution_datetime_naive = datetime.combine(execution_date, time(5, 59, 45))
            execution_datetime_utc = execution_datetime_naive.astimezone(pytz.UTC).replace(tzinfo=None)
            execution_time_display = execution_datetime_naive.strftime('%A, %B %d, %Y at %I:%M:%S %p %Z')
        
        print(f"   Will execute: {execution_time_display}")
        
        confirm = input("\n✅ Confirm booking? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Booking cancelled")
            return
        
        # Create the booking request
        try:
            booking_id = create_booking_request(
                user_name,
                requested_date,
                requested_time,
                execution_datetime_utc
            )
            
            print(f"\n🎉 Booking request created successfully!")
            print(f"   Booking ID: {booking_id}")
            print(f"   Status: Pending")
            
            if is_immediate_booking:
                print(f"   🚀 IMMEDIATE BOOKING - Celery Beat will pick this up within 5 minutes!")
                print(f"   📱 Watch the logs with: docker-compose logs -f celery-worker")
            else:
                print(f"   ⏰ Scheduled execution: {execution_time_display}")
            
            print(f"   ✅ Booking scheduled in database")
            print(f"   📅 Celery Beat will automatically pick this up based on scheduled_for time")
            
            if is_immediate_booking:
                print(f"\n🔥 TESTING MODE - Watch for immediate booking!")
                print(f"   • Check celery-worker logs to see the booking attempt")
                print(f"   • The scraper will navigate to Jeremy Ranch and book your tee time")
                print(f"   • If successful, you'll have a real tee time reservation!")
            else:
                print(f"\n📝 Important Notes:")
                print(f"   • Keep your computer/server running until {execution_date.strftime('%B %d')}")
                print(f"   • The booking will attempt exactly 7 days before your requested date")
                print(f"   • If your preferred time isn't available, the closest time will be booked")
            
        except Exception as e:
            print(f"❌ Failed to create booking: {e}")
            return
        
    except KeyboardInterrupt:
        print("\n❌ Booking cancelled by user")
        return
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return

def list_bookings():
    """List all current booking requests"""
    try:
        from src.models import get_all_bookings
        
        bookings = get_all_bookings()
        
        if not bookings:
            print("📋 No booking requests found")
            return
        
        print(f"📋 Current Booking Requests ({len(bookings)} total)")
        print("=" * 80)
        
        for booking in bookings:
            status_emoji = {
                'pending': '⏳',
                'running': '🏃',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }.get(booking.status, '❓')
            
            print(f"{status_emoji} ID: {booking.id}")
            print(f"   Name: {booking.user_name}")
            print(f"   Date: {booking.requested_date.strftime('%A, %B %d, %Y')}")
            print(f"   Time: {booking.requested_time.strftime('%I:%M %p')}")
            print(f"   Status: {booking.status.title()}")
            print(f"   Created: {booking.created_at.strftime('%m/%d/%Y %I:%M %p')}")
            
            if booking.scheduled_for:
                mtn_tz = pytz.timezone('MST')
                scheduled_mtn = pytz.UTC.localize(booking.scheduled_for).astimezone(mtn_tz)
                print(f"   Executes: {scheduled_mtn.strftime('%A, %B %d at %I:%M:%S %p %Z')}")
            
            if booking.booked_time:
                print(f"   Booked Time: {booking.booked_time.strftime('%I:%M %p')}")
            
            if booking.error_message:
                print(f"   Error: {booking.error_message}")
            
            print(f"   Attempts: {booking.attempts}")
            print()
            
    except Exception as e:
        print(f"❌ Error listing bookings: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_bookings()
    else:
        main()