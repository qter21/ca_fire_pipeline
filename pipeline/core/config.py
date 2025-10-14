"""Configuration settings for CA Fire Pipeline"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Firecrawl Configuration
    FIRECRAWL_API_KEY: str
    FIRECRAWL_BASE_URL: str = "https://api.firecrawl.dev"
    FIRECRAWL_TIMEOUT: int = 60  # Request timeout in seconds
    FIRECRAWL_REQUEST_TIMEOUT: int = 90  # Individual request timeout (includes retries)

    # MongoDB Configuration
    MONGODB_URI: str = "mongodb://admin:legalcodes123@mongodb:27017/ca_codes_db?authSource=admin"
    MONGODB_DATABASE: str = "ca_codes_db"

    # Pipeline Configuration
    API_PORT: int = 8001
    BATCH_SIZE: int = 50
    MAX_CONCURRENT_REQUESTS: int = 5
    CACHE_MAX_AGE: int = 172800000  # 2 days in milliseconds

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def mongodb_uri(self) -> str:
        """Get MongoDB URI (lowercase property for consistency)."""
        return self.MONGODB_URI


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the settings singleton.

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# For backward compatibility
settings = get_settings()
