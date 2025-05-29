# src/models.py
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, date, time
from typing import List, Optional
from .config import get_settings

settings = get_settings()

# Database setup with PostgreSQL optimizations
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug  # SQL logging in debug mode
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BookingRequest(Base):
    __tablename__ = "booking_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(100), nullable=False, index=True)
    requested_date = Column(Date, nullable=False, index=True)
    requested_time = Column(Time, nullable=False)
    status = Column(String(20), default='pending', index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    scheduled_for = Column(DateTime, nullable=False, index=True)
    attempts = Column(Integer, default=0)
    last_attempt = Column(DateTime)
    booked_time = Column(Time)
    error_message = Column(Text)
    
    # PostgreSQL-specific indexes for better performance
    __table_args__ = (
        Index('idx_booking_status_scheduled', 'status', 'scheduled_for'),
        Index('idx_booking_user_date', 'user_name', 'requested_date'),
    )

class BookingHistory(Base):
    __tablename__ = "booking_history"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    details = Column(JSONB)  # Use PostgreSQL JSONB for better performance
    success = Column(Boolean)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_booking_request(user_name: str, requested_date: date, 
                         requested_time: time, scheduled_for: datetime) -> int:
    """Create a new booking request"""
    db = SessionLocal()
    try:
        booking = BookingRequest(
            user_name=user_name,
            requested_date=requested_date,
            requested_time=requested_time,
            scheduled_for=scheduled_for
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking.id
    finally:
        db.close()

def get_booking_request(booking_id: int) -> Optional[BookingRequest]:
    """Get a booking request by ID"""
    db = SessionLocal()
    try:
        return db.query(BookingRequest).filter(BookingRequest.id == booking_id).first()
    finally:
        db.close()

def get_pending_bookings(current_time: datetime) -> List[BookingRequest]:
    """Get bookings that should be executed now"""
    db = SessionLocal()
    try:
        return db.query(BookingRequest).filter(
            BookingRequest.status == 'pending',
            BookingRequest.scheduled_for <= current_time
        ).all()
    finally:
        db.close()

def update_booking_status(booking_id: int, status: str, success: bool = None, 
                         error: str = None, booked_time: time = None):
    """Update booking request status"""
    db = SessionLocal()
    try:
        booking = db.query(BookingRequest).filter(BookingRequest.id == booking_id).first()
        if booking:
            booking.status = status
            booking.last_attempt = datetime.utcnow()
            booking.attempts += 1
            
            if error:
                booking.error_message = error
            if booked_time:
                booking.booked_time = booked_time
                
            # Add to history with JSONB data
            history_details = {
                "status": status,
                "attempt_number": booking.attempts,
                "timestamp": datetime.utcnow().isoformat()
            }
            if error:
                history_details["error"] = error
            if booked_time:
                history_details["booked_time"] = booked_time.strftime('%H:%M:%S')
                
            history = BookingHistory(
                request_id=booking_id,
                action=status,
                success=success,
                details=history_details
            )
            db.add(history)
            db.commit()
    finally:
        db.close()

def get_all_bookings() -> List[BookingRequest]:
    """Get all booking requests"""
    db = SessionLocal()
    try:
        return db.query(BookingRequest).all()
    finally:
        db.close()