-- init.sql
-- Database initialization script

-- Create booking requests table
CREATE TABLE IF NOT EXISTS booking_requests (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL,
    requested_date DATE NOT NULL,
    requested_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP NOT NULL,
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    booked_time TIME,
    error_message TEXT
);

-- Create booking history table
CREATE TABLE IF NOT EXISTS booking_history (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES booking_requests(id),
    action VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB,
    success BOOLEAN
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_booking_requests_scheduled_for ON booking_requests(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_booking_requests_status ON booking_requests(status);
CREATE INDEX IF NOT EXISTS idx_booking_history_request_id ON booking_history(request_id);

-- Insert sample data (optional)
-- INSERT INTO booking_requests (user_name, requested_date, requested_time, scheduled_for) 
-- VALUES ('John Doe', '2025-06-08', '11:00:00', '2025-06-01 00:00:00');