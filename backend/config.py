from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    # Supabase Configuration
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    
    # Apollo.io Configuration
    APOLLO_API_KEY: Optional[str] = None
    
    # Google Custom Search Configuration
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None
    GOOGLE_SHEETS_CREDENTIALS: Optional[str] = None
    
    # Apify Configuration
    APIFY_API_TOKEN: str = ""
    
    # Resend Configuration
    RESEND_API_KEY: str = ""
    RESEND_WEBHOOK_SECRET: Optional[str] = None
    
    # Application Configuration
    BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Email Configuration
    FROM_EMAIL: str = "noreply@yourdomain.com"
    SENDER_EMAIL: Optional[str] = None
    MAX_DAILY_EMAILS: int = 100
    
    # Database Configuration
    DATABASE_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # API Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

# Environment-specific configurations
class DevelopmentSettings(Settings):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

class ProductionSettings(Settings):
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"

class TestingSettings(Settings):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    # Override with test database
    SUPABASE_URL: str = "test_supabase_url"
    SUPABASE_SERVICE_ROLE_KEY: str = "test_key"

def get_settings_by_env(env: str = None) -> Settings:
    """Get settings based on environment"""
    if env is None:
        env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()