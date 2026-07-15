"""
QFlow Configuration — Pydantic Settings.
Loads from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "QFlow"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://qflow:qflow_dev_2026@localhost:5432/qflow"
    DATABASE_URL_SYNC: str = "postgresql://qflow:qflow_dev_2026@localhost:5432/qflow"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # JWT Auth
    SECRET_KEY: str = "qflow-dev-secret-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @model_validator(mode="after")
    def set_celery_urls(self):
        if self.CELERY_BROKER_URL == "redis://localhost:6379/0" and self.REDIS_URL != "redis://localhost:6379/0":
            self.CELERY_BROKER_URL = self.REDIS_URL
        if self.CELERY_RESULT_BACKEND == "redis://localhost:6379/1" and self.REDIS_URL != "redis://localhost:6379/0":
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        return self

@lru_cache()
def get_settings() -> Settings:
    return Settings()
