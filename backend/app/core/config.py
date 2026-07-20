from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "leads@datamart.com"
    NOTIFICATION_EMAIL: str = "cto@datamart.com"
    
    # Slack
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    # App
    APP_URL: str = "http://localhost:8000"
    COMPANY_NAME: str = "Datamart Inc."
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields

settings = Settings()
