"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration. All secrets from environment variables."""

    APP_NAME: str = "Nivaas"
    APP_DESCRIPTION: str = "Find a property by describing what you need."

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.8-27b"

    TAVILY_API_KEY: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/nivaas"
    DATABASE_URL_SYNC: str = "postgresql://user:password@localhost:5432/nivaas"

    DEMO_MODE: bool = False
    DAILY_TAVILY_CREDIT_CAP: int = 40
    MAX_TAVILY_CALLS_PER_MESSAGE: int = 3

    # Authentication & JWT
    JWT_SECRET_KEY: str = "nivaas-dev-secret-key-change-in-production-12345"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    OPERATOR_NAME: str = ""
    CONTACT_EMAIL: str = "1774.sparsh@gmail.com"
    JURISDICTION_CITY: str = ""
    LAST_UPDATED: str = "20 September 2026"

    MAX_MESSAGE_LENGTH: int = 2000
    MAX_TOOL_ITERATIONS: int = 5

    LISTING_CACHE_HOURS: int = 24
    LOCALITY_CACHE_DAYS: int = 7
    SESSION_RETENTION_DAYS: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()


# Shared constants
DEFAULT_WEIGHTS: dict[str, float] = {
    "budget_fit": 0.25,
    "location": 0.25,
    "connectivity": 0.15,
    "area": 0.10,
    "amenities": 0.10,
    "property_type": 0.05,
    "furnishing": 0.05,
    "parking": 0.05,
}

WEIGHT_LABELS: dict[str, str] = {
    "budget_fit": "Budget fit",
    "location": "Location match",
    "connectivity": "Metro and IT park proximity",
    "area": "Carpet area",
    "amenities": "Amenities",
    "property_type": "Property type",
    "furnishing": "Furnishing",
    "parking": "Parking",
}

SEARCH_DOMAINS: list[str] = [
    "magicbricks.com",
    "99acres.com",
    "housing.com",
    "nobroker.in",
    "squareyards.com",
]
