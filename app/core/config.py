from typing import List, Optional
from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings
import secrets


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://localhost:5173",
    ]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: str = "postgresql://mealsplit:password@localhost:5432/mealsplit"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # External APIs
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    GEMINI_TEXT_MODEL: str = "gemini-1.5-flash"
    SPLITWISE_CLIENT_ID: Optional[str] = None
    SPLITWISE_CLIENT_SECRET: Optional[str] = None
    SPLITWISE_REDIRECT_URI: str = "http://localhost:8000/api/v1/splitwise/oauth/callback"

    # File Storage
    UPLOAD_DIR: str = "/tmp/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Email (for future notifications)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: Optional[str] = None

    # Testing
    TESTING: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
