# src/api.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, validator
from datetime import datetime, date, time, timedelta
from typing import List, Optional
import pytz
from sqlalchemy.orm import Session

from .models import get_db, BookingRequest, BookingHistory, create_booking_request, get_all_bookings, get_booking_request
from .scheduler import schedule_booking
from .config import get_settings

app = FastAPI(
    title="Golf Booking Automation API",
    description="Automated tee time booking system for Jeremy Ranch Golf Club",
    version="1.0.0"
)

settings = get_settings()

# Pydantic models for API
class BookingRequestCreate(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=100, description="Name for the booking")
    requested_date: date = Field(..., description="Date for tee time (YYYY-MM-DD)")
    requested_time: str = Field(..., description="Preferred time (HH:MM in 24-hour format, e.g., '08:00')")
    
    @validator('requested_date')
    def validate_future_date(cls, v):
        mtn_tz = pytz.timezone('MST')
        today = datetime.now(mtn_tz).date()
        
        if v <= today:
            raise ValueError('Requested date must be in the future')
        
        # Must be more than 7 days out (since we book exactly 7 days prior)
        if v <= today + timedelta(days=7):
            raise ValueError('Requested date must be more than 7 days in the future')
        
        # Don't allow bookings too far out (optional limit)
        if v > today + timedelta(days=60):
            raise ValueError('Requested date cannot be more than 60 days in the future')
        
        return v
    
    @validator('requested_time')
    def validate_time_format(cls, v):
        try:
            # Parse time to validate format
            time_obj = datetime.strptime(v, '%H:%M').time()
            
            # Validate reasonable golf hours (6 AM to 6 PM)
            if time_obj < time(6, 0) or time_obj > time(18, 0):
                raise ValueError('Requested time must be between 06:00 and 18:00')
            
            return v
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError('Time must be in HH:MM format (e.g., "08:00")')
            raise e

class BookingRequestResponse(BaseModel):
    id: int
    user_name: str
    requested_date: date
    requested_time: time
    status: str
    created_at: datetime
    scheduled_for: datetime
    attempts: int
    last_attempt: Optional[datetime]
    booked_time: Optional[time]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

class BookingStatusUpdate(BaseModel):
    status: str = Field(..., regex="^(pending|running|completed|failed|cancelled)$")

# Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    """Simple HTML interface for the API"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Golf Booking Automation</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .container { background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0; }
            input, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #007bff; color: white; cursor: pointer; }
            button:hover { background: #0056b3; }
            .booking { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
            .status-pending { border-left-color: #ffc107; }
            .status-completed { border-left-color: #28a745; }
            .status-failed { border-left-color: #dc3545; }
        </style>
    </head>
    <body>
        <h1>🏌️ Golf Booking Automation</h1>
        <p>Automatically book Jeremy Ranch Golf Club tee times exactly 7 days in advance!</p>
        
        <div class="container">
            <h2>📅 Schedule a New Booking</h2>
            <form id="bookingForm">
                <div>
                    <label>Your Name:</label><br>
                    <input type="text" id="userName" placeholder="John Doe" required>
                </div>
                <div>
                    <label>Requested Date:</label><br>
                    <input type="date" id="requestedDate" required>
                </div>
                <div>
                    <label>Preferred Time:</label><br>
                    <input type="time" id="requestedTime" value="08:00" required>
                </div>
                <button type="submit">Schedule Booking</button>
            </form>
        </div>
        
        <div class="container">
            <h2>📋 Your Bookings</h2>
            <button onclick="loadBookings()">Refresh Bookings</button>
            <div id="bookingsList"></div>
        </div>
        
        <script>
            // Set minimum date to 8 days from now
            const today = new Date();
            const minDate = new Date(today.getTime() + (8 * 24 * 60 * 60 * 1000));
            document.getElementById('requestedDate').min = minDate.toISOString().split('T')[0];
            
            document.getElementById('bookingForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = {
                    user_name: document.getElementById('userName').value,
                    requested_date: document.getElementById('requestedDate').value,
                    requested_time: document.getElementById('requestedTime').value
                };
                
                try {
                    const response = await fetch('/book', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(formData)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        alert('Booking scheduled successfully!');
                        document.getElementById('bookingForm').reset();
                        loadBookings();
                    } else {
                        alert('Error: ' + (result.detail || 'Unknown error'));
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            });
            
            async function loadBookings() {
                try {
                    const response = await fetch('/bookings');
                    const bookings = await response.json();
                    
                    const container = document.getElementById('bookingsList');
                    if (bookings.length === 0) {
                        container.innerHTML = '<p>No bookings found.</p>';
                        return;
                    }
                    
                    container.innerHTML = bookings.map(booking => `
                        <div class="booking status-${booking.status}">
                            <h3>${booking.user_name}</h3>
                            <p><strong>Date:</strong> ${booking.requested_date}</p>
                            <p><strong>Time:</strong> ${booking.requested_time}</p>
                            <p><strong>Status:</strong> ${booking.status}</p>
                            <p><strong>Scheduled For:</strong> ${new Date(booking.scheduled_for).toLocaleString()}</p>
                            ${booking.booked_time ? `<p><strong>Booked Time:</strong> ${booking.booked_time}</p>` : ''}
                            ${booking.error_message ? `<p><strong>Error:</strong> ${booking.error_message}</p>` : ''}
                            <p><strong>Attempts:</strong> ${booking.attempts}</p>
                        </div>
                    `).join('');
                } catch (error) {
                    document.getElementById('bookingsList').innerHTML = '<p>Error loading bookings.</p>';
                }
            }
            
            // Load bookings on page load
            loadBookings();
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/book", response_model=BookingRequestResponse)
async def create_booking_request(
    booking_request: BookingRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new booking request"""
    try:
        # Parse the time
        requested_time_obj = datetime.strptime(booking_request.requested_time, '%H:%M').time()
        
        # Calculate execution time (7 days prior at 11:59:50 PM Mountain Time)
        mtn_tz = pytz.timezone('MST')
        
        # Get the date 7 days before the requested date
        execution_date = booking_request.requested_date - timedelta(days=7)
        
        # Set execution time to 11:59:50 PM on that date
        execution_datetime_naive = datetime.combine(execution_date, time(23, 59, 50))
        
        # Localize to Mountain Time, then convert to UTC for storage
        execution_datetime_mtn = mtn_tz.localize(execution_datetime_naive)
        execution_datetime_utc = execution_datetime_mtn.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Create booking request in database
        booking_id = create_booking_request(
            user_name=booking_request.user_name,
            requested_date=booking_request.requested_date,
            requested_time=requested_time_obj,
            scheduled_for=execution_datetime_utc
        )
        
        # Schedule the Celery task
        background_tasks.add_task(
            schedule_booking_task,
            booking_request.user_name,
            booking_request.requested_date.isoformat(),
            booking_request.requested_time
        )
        
        # Return the created booking
        created_booking = get_booking_request(booking_id)
        if not created_booking:
            raise HTTPException(status_code=500, detail="Failed to retrieve created booking")
        
        return created_booking
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create booking: {str(e)}")

@app.get("/bookings", response_model=List[BookingRequestResponse])
async def get_bookings(db: Session = Depends(get_db)):
    """Get all booking requests"""
    try:
        bookings = get_all_bookings()
        return bookings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve bookings: {str(e)}")

@app.get("/bookings/{booking_id}", response_model=BookingRequestResponse)
async def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Get a specific booking request"""
    booking = get_booking_request(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.delete("/bookings/{booking_id}")
async def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    """Cancel a booking request (only if pending)"""
    from .models import update_booking_status
    
    booking = get_booking_request(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status != 'pending':
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel booking with status: {booking.status}"
        )
    
    try:
        update_booking_status(booking_id, 'cancelled', success=False)
        return {"message": "Booking cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel booking: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "golf_club": settings.golf_club_url
    }

# Background task function
def schedule_booking_task(user_name: str, requested_date: str, requested_time: str):
    """Background task to schedule the booking with Celery"""
    try:
        # This calls the Celery task to handle the scheduling
        from .scheduler import schedule_booking
        result = schedule_booking.delay(user_name, requested_date, requested_time)
        return result
    except Exception as e:
        print(f"Error scheduling booking task: {e}")
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)