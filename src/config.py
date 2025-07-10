import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application configuration using Pydantic BaseSettings for type-safe environment variable handling."""
    
    # Database settings
    database_url: str = Field(default="sqlite:////tmp/dwell/dwell.db", description="Database connection URL")
    
    # Email settings
    email_username: Optional[str] = Field(default=None, description="Email username for SMTP authentication")
    email_password: Optional[str] = Field(default=None, description="Email password for SMTP authentication")
    smtp_server: str = Field(default="smtp.gmail.com", description="SMTP server address")
    smtp_port: int = Field(default=587, description="SMTP server port")
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for AI features")
    
    # Listings Project credentials
    listings_email: Optional[str] = Field(default=None, description="Email for Listings Project authentication")
    listings_password: Optional[str] = Field(default=None, description="Password for Listings Project authentication")
    
    # Application settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    env: str = Field(default="development", description="Environment (development, test, production)")

    model_config = SettingsConfigDict(
        env_file='.env.test' if os.getenv('ENV') == 'test' else '.env', 
        env_file_encoding='utf-8'
    )
    


# Global settings instance
settings = Settings()
