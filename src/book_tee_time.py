#!/usr/bin/env python3
# book_tee_time.py - Simple CLI for booking tee times

import sys
import os
from datetime import datetime, date, time, timedelta
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
        
        # Validate date is in future and more than 7 days out
        today = date.today()
        if requested_date <= today:
            print("❌ Date must be in the future")
            return
        
        if requested_date <= today + timedelta(days=7):
            print("❌ Date must be more than 7 days in the future")
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
        print(f"   Date: {requested_date.strftime('%A, %B %d, %Y')}")
        print(f"   Time: {requested_time.strftime('%I:%M %p')}")
        
        # Calculate execution time
        mtn_tz = pytz.timezone('MST')
        execution_date = requested_date - timedelta(days=7)
        execution_datetime_naive = datetime.combine(execution_date, time(23, 59, 50))
        execution_datetime_mtn = mtn_tz.localize(execution_datetime_naive)
        execution_datetime_utc = execution_datetime_mtn.astimezone(pytz.UTC).replace(tzinfo=None)
        
        print(f"   Will execute: {execution_datetime_mtn.strftime('%A, %B %d, %Y at %I:%M:%S %p %Z')}")
        
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
            print(f"   Execution: {execution_datetime_mtn.strftime('%A, %B %d at %I:%M:%S %p %Z')}")
            
            print(f"   ✅ Booking scheduled in database")
            print(f"   📅 Celery Beat will automatically pick this up based on scheduled_for time")
            
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