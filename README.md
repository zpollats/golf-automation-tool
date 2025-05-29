# Golf Booking Automation

Automated tee time booking system that books golf tee times exactly 7 days in advance at midnight.

## Features

- 🏌️ Automated tee time booking
- ⏰ Scheduled booking 7 days in advance
- 🎯 Finds closest available time to your preference
- 📧 Email/SMS notifications for failures
- 🐳 Fully containerized with Docker
- 📊 PostgreSQL database for request tracking
- 🔄 Retry logic with exponential backoff

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/golf-booking-automation.git
cd golf-booking-automation
```

### 2. Configure Environment

```bash
# Copy the environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or your preferred editor
```

**Required Configuration:**
- `GOLF_CLUB_URL`: Your golf club's booking website
- `GOLF_USERNAME`: Your login username
- `GOLF_PASSWORD`: Your login password
- Notification settings (Twilio for SMS, SendGrid for email)

### 3. Start the System

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 4. Make a Booking Request

```bash
# Example: Book for June 8th at 11:00 AM
curl -X POST "http://localhost:8000/book" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "John Doe",
    "requested_date": "2025-06-08",
    "requested_time": "11:00"
  }'
```

## Architecture

- **golf-booking-app**: Main application and API
- **postgres**: Database for storing booking requests
- **redis**: Task queue for scheduled jobs
- **selenium-chrome**: Headless browser for web scraping
- **celery-worker**: Background task processor
- **celery-beat**: Scheduled task dispatcher

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| API | 8000 | REST API for booking requests |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Task queue |
| Selenium Grid | 4444 | Web browser automation |
| VNC (optional) | 7900 | Browser debugging |

## Environment Variables

See `.env.example` for all available configuration options.

### Critical Settings

```bash
# Your golf club credentials
GOLF_USERNAME=your_username
GOLF_PASSWORD=your_password
GOLF_CLUB_URL=https://your-club-website.com

# Notification settings for alerts
ALERT_EMAIL=your_email@example.com
ALERT_PHONE_NUMBER=+1234567890
```

## Usage Examples

### Schedule a Booking

```python
import requests

# Book tee time for next Sunday at 10:30 AM
response = requests.post("http://localhost:8000/book", json={
    "user_name": "Your Name",
    "requested_date": "2025-06-08",
    "requested_time": "10:30"
})
```

### Check Booking Status

```bash
# View all pending bookings
curl http://localhost:8000/bookings

# Check specific booking
curl http://localhost:8000/bookings/1
```

## Development

### Running Tests

```bash
docker-compose exec golf-booking-app pytest
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f golf-booking-app
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U golf_user -d golf_booking
```

## Troubleshooting

### Common Issues

1. **Login Failures**: Check your credentials in `.env`
2. **Site Changes**: Golf club websites may update their HTML structure
3. **Timing Issues**: Ensure your system clock is accurate

### Debug Mode

Set `DEBUG=true` in `.env` to enable:
- Non-headless browser mode
- Detailed logging
- Screenshot capture on failures

### Browser Debugging

Access the Selenium Grid console at `http://localhost:4444` to monitor browser sessions.

## Security Notes

- Never commit `.env` files to version control
- Use strong, unique passwords
- Consider using environment-specific configurations
- Regularly rotate API keys and credentials

## Deployment

### For Multiple Users

Each user needs their own `.env` file with their specific credentials:

```bash
# User 1
cp .env.example .env.user1
# Edit .env.user1 with User 1's credentials

# User 2  
cp .env.example .env.user2
# Edit .env.user2 with User 2's credentials
```

Then run with specific env files:
```bash
docker-compose --env-file .env.user1 up -d
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

**⚠️ Disclaimer**: This tool automates interactions with golf club websites. Ensure you comply with your golf club's terms of service and booking policies.