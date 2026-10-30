import os
from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AstraChain API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    DATABASE_URL: str = "sqlite:///./astrachain.db"

    SECRET_KEY: str = "astrachain-super-secret-key-change-in-production-environment"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "*",
    ]

    LOG_LEVEL: str = "INFO"

    GROQ_API_KEY: Union[str, None] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    # Hard cap for a single Groq HTTP call, and how long agents skip the LLM after it fails
    GROQ_TIMEOUT_SECONDS: float = 20.0
    GROQ_COOLDOWN_SECONDS: float = 60.0

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
