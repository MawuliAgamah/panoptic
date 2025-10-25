"""
Configuration for the FastAPI web server
"""
import os
from typing import List

class WebConfig:
    """Configuration class for the web server"""
    
    # Server settings
    HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("WEB_PORT", "8000"))
    DEBUG: bool = os.getenv("WEB_DEBUG", "true").lower() == "true"
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]
    
    # API settings
    API_TITLE: str = "AI Module API"
    API_DESCRIPTION: str = "API for managing flashcards and knowledge graphs"
    API_VERSION: str = "0.1.0"
    
    # Database settings (if needed for web-specific config)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./database.db")
    
    @classmethod
    def get_cors_origins(cls) -> List[str]:
        """Get CORS origins, including any from environment"""
        origins = cls.CORS_ORIGINS.copy()
        env_origins = os.getenv("CORS_ORIGINS", "")
        if env_origins:
            origins.extend(env_origins.split(","))
        return origins
