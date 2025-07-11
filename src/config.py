import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration using Pydantic BaseSettings for type-safe environment variable handling."""

    # Database settings
    database_url: str = Field(
        default="sqlite:////tmp/dwell/dwell.db", description="Database connection URL"
    )

    # Email settings
    email_username: Optional[str] = Field(
        default=None, description="Email username for SMTP authentication"
    )
    email_password: Optional[str] = Field(
        default=None, description="Email password for SMTP authentication"
    )
    smtp_server: str = Field(
        default="smtp.gmail.com", description="SMTP server address"
    )
    smtp_port: int = Field(default=587, description="SMTP server port")

    # OpenAI settings
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key for AI features"
    )

    # Listings Project credentials
    listings_email: Optional[str] = Field(
        default=None, description="Email for Listings Project authentication"
    )
    listings_password: Optional[str] = Field(
        default=None, description="Password for Listings Project authentication"
    )

    # Application settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    env: str = Field(
        default="development", description="Environment (development, test, production)"
    )

    # Redis/Celery settings
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis URL for Celery"
    )
    celery_broker_url: Optional[str] = Field(
        default=None, description="Celery broker URL (defaults to redis_url)"
    )
    celery_result_backend: Optional[str] = Field(
        default=None, description="Celery result backend (defaults to redis_url)"
    )

    model_config = SettingsConfigDict(
        env_file=".env.test" if os.getenv("ENV") == "test" else ".env",
        env_file_encoding="utf-8",
    )

    @property
    def effective_celery_broker_url(self) -> str:
        """Get effective Celery broker URL (falls back to redis_url)"""
        return self.celery_broker_url or self.redis_url

    @property
    def effective_celery_result_backend(self) -> str:
        """Get effective Celery result backend URL (falls back to redis_url)"""
        return self.celery_result_backend or self.redis_url


# Global settings instance
settings = Settings()
