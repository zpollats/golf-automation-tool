# src/config.py
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import logging

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Golf Club Configuration
    golf_club_url: str
    golf_username: str
    golf_password: str
    
    # Database
    database_url: str = "postgresql://golf_user:golf_pass@postgres:5432/golf_booking"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Selenium
    selenium_hub_url: str = "http://localhost:4444"
    headless_browser: bool = True
    
    # Notifications
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    alert_phone_number: Optional[str] = None
    
    sendgrid_api_key: Optional[str] = None
    alert_email: Optional[str] = None
    from_email: Optional[str] = None
    
    # Application Settings
    log_level: str = "INFO"
    retry_attempts: int = 5
    retry_delay_minutes: int = 5
    max_retry_duration_minutes: int = 30
    
    # Development
    debug: bool = False
    
    @field_validator('golf_club_url')
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Golf club URL must start with http:// or https://')
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False
    )

# Global settings instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log')
    ]
)

logger = logging.getLogger(__name__)

def get_settings() -> Settings:
    """Get application settings"""
    return settings

def validate_required_settings():
    """Validate that all required settings are present"""
    required_fields = [
        'golf_club_url',
        'golf_username', 
        'golf_password'
    ]
    
    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field, None):
            missing_fields.append(field.upper())
    
    if missing_fields:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    logger.info("Configuration validation passed")
    return True