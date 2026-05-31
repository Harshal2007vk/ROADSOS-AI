from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    APP_NAME: str = "ROADSoS AI"
    DEBUG: bool = True
    SECRET_KEY: str = secrets.token_urlsafe(32)
    DATABASE_URL: str = "sqlite:///./roadsos.db"
    GEMINI_API_KEY: Optional[str] = None
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"
    MAX_SEARCH_RADIUS_M: int = 10000
    DEFAULT_SEARCH_RADIUS_M: int = 5000
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50
    SESSION_MAX_AGE: int = 86400 * 7  # 7 days

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
