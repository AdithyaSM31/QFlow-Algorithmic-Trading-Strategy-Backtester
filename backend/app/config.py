"""
QFlow Configuration — Pydantic Settings.
Loads from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()
