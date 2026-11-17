import os
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "MediSync AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database Settings
    POSTGRES_USER: str = "medisync_user"
    POSTGRES_PASSWORD: str = "medisync_password"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "medisync_db"

    # Async & Sync Connection Strings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://medisync_user:medisync_password@localhost:5432/medisync_db",
        description="Async database connection string for FastAPI using asyncpg"
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql+psycopg2://medisync_user:medisync_password@localhost:5432/medisync_db",
        description="Sync database connection string for Celery and Alembic using psycopg2"
    )

    # Redis & Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # JWT Authentication
    SECRET_KEY: str = "dev_insecure_secret_key_change_in_production_medi_sync_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Vector & RAG Configuration
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # LLM Provider Configuration
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Encryption Key for API Integration Credentials
    CREDENTIAL_ENCRYPTION_KEY: str = "gK7K-q_X1xMvP0R5K-q_X1xMvP0R5K-q_X1xMvP0R5E="

    # CORS Settings
    BACKEND_CORS_ORIGINS: Union[List[str], str] = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

