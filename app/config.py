"""Application configuration using Pydantic settings."""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    app_name: str = "RenderCV Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS Settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://beta.resumit.tech",
        "https://resumit.tech",
        "https://www.resumit.tech",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # RenderCV Settings
    default_theme: str = "classic"
    output_dir: str = "/tmp/rendercv_output"
    max_file_size_mb: int = 10
    cleanup_after_render: bool = True
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Caching
    cache_ttl: int = 300  # seconds
    cache_max_size: int = 100
    
    # Redis Cache
    redis_url: str | None = None
    redis_tls: bool = False

    # Gemini API for resume parsing
    gemini_api_key: str | None = None

    class Config:
        env_prefix = "RENDERCV_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

