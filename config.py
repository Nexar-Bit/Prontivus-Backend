from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings - All values are loaded from .env file automatically"""
    
    # API Settings
    APP_NAME: str = "Prontivus API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database Settings
    DATABASE_URL: str = "mysql+aiomysql://user:password@localhost:3306/prontivus_clinic"
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server Settings (optional)
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Email Settings (optional)
    SMTP_HOST: Optional[str] = "smtpout.secureserver.net"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "suporte@prontivus.com"
    
    # Push Notification Settings (optional)
    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_EMAIL: str = "mailto:noreply@prontivus.com"
    
    # Google OAuth Settings (optional)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/google/callback"
    
    # SMS Settings (optional)
    SMS_PROVIDER: str = "twilio"
    SMS_TWILIO_ACCOUNT_SID: Optional[str] = None
    SMS_TWILIO_AUTH_TOKEN: Optional[str] = None
    SMS_TWILIO_FROM_NUMBER: Optional[str] = None
    
    # OpenAI API Key (for voice transcription)
    OPENAI_API_KEY: Optional[str] = None
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra fields from .env
    }

settings = Settings()

