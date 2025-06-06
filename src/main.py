# src/main.py
import logging
import uvicorn
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
        
        # Start FastAPI server
        logger.info("Starting FastAPI server on port 8000...")
        uvicorn.run(
            "src.api:app",
            host="0.0.0.0",
            port=8000,
            reload=settings.debug,
            log_level=settings.log_level.lower()
        )
            
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()