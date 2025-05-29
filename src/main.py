# src/main.py
import logging
from .config import validate_required_settings, get_settings
from .models import Base, engine

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    try:
        # Validate configuration
        validate_required_settings()
        settings = get_settings()
        
        logger.info("Starting Golf Booking Application")
        logger.info(f"Golf Club URL: {settings.golf_club_url}")
        logger.info(f"Database: {settings.database_url}")
        logger.info(f"Redis: {settings.redis_url}")
        
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        # Keep the application running
        logger.info("Application started successfully. Celery workers will handle booking tasks.")
        
        # In a real deployment, this might start a web server or other services
        import time
        while True:
            time.sleep(60)  # Keep alive
            
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()