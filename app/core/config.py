from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application configuration settings."""

    # Application
    APP_NAME: str = Field(default="Insurance Intermediary Backend", alias="APP_NAME")
    APP_DESCRIPTION: str = Field(
        default="Multi-tenant insurance policy intermediary platform",
        alias="APP_DESCRIPTION",
    )
    APP_VERSION: str = Field(default="1.0.0", alias="APP_VERSION")
    ENVIRONMENT: str = Field(default="dev", alias="ENVIRONMENT")
    DEBUG: bool = Field(default=False, alias="DEBUG")
    
    LOG_LEVEL: str = "INFO"
    # LOG_LEVEL: str = "DEBUG"
    DB_ECHO: bool = Field(default=False, alias="DB_ECHO")
    ALLOWED_ORIGINS: List[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")
    
    APP_CODE: str = "soat"
    USE_SECRETS_MANAGER: bool = Field(default=False)
    AWS_REGION: str = Field(default="us-east-1")
    AWS_STAGE: str = Field(default="dev", alias="AWS_STAGE")
    COGNITO_USER_POOL_ID: Optional[str] = Field(default=None, alias="COGNITO_USER_POOL_ID")
    COGNITO_APP_CLIENT_ID: Optional[str] = Field(default=None, alias="COGNITO_APP_CLIENT_ID")
    USE_COGNITO: bool = Field(default=False)
    
    # Will be populated dynamically
    secrets_loaded: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()