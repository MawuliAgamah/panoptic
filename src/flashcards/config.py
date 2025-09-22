"""
Flashcard Module Configuration

Centralized configuration for all flashcard system settings.
This file contains all configurable parameters used throughout the flashcard module.
"""

from typing import Dict, Any
import os
from pathlib import Path


class FlashcardConfig:
    """Centralized configuration for the flashcard system"""

    # === DATABASE AND STORAGE ===
    DATABASE_PATH = "database/flashcards"
    DATABASE_BACKUP_ENABLED = True
    DATABASE_JSON_INDENT = 2
    
    # Database file names
    DECKS_FILENAME = "decks.json"
    CARDS_FILENAME = "cards.json"
    REVIEWS_FILENAME = "reviews.json"
    USERS_FILENAME = "users.json"

    # === ALGORITHM CONFIGURATION ===
    DEFAULT_ALGORITHM = "sm2"
    AVAILABLE_ALGORITHMS = ['sm2', 'sm15', 'experimental']
    
    # SM2 Algorithm Settings
    SM2_DEFAULT_EASE_FACTOR = 2.5
    SM2_MIN_EASE_FACTOR = 1.3
    SM2_MIN_INTERVAL_DAYS = 1
    SM2_MAX_INTERVAL_DAYS = 365
    SM2_INITIAL_INTERVAL_SUCCESS = 6  # Second review interval for correct answers
    SM2_QUALITY_SCALE_MIN = 0
    SM2_QUALITY_SCALE_MAX = 5
    SM2_SUCCESS_THRESHOLD = 3  # Quality >= 3 is considered successful
    
    # SM15 Algorithm Settings
    SM15_DEFAULT_EASE_FACTOR = 2.5
    SM15_MIN_EASE_FACTOR = 1.3
    SM15_MAX_EASE_FACTOR = 3.0
    SM15_MIN_INTERVAL_DAYS = 1
    SM15_MAX_INTERVAL_DAYS = 365
    SM15_DEFAULT_DIFFICULTY = 0.3
    SM15_QUALITY_SCALE_MIN = 1
    SM15_QUALITY_SCALE_MAX = 4
    SM15_SUCCESS_THRESHOLD = 3

    # === CONTENT VALIDATION ===
    # Text length limits
    CARD_FRONT_MAX_LENGTH = None  # No limit (was 500)
    CARD_BACK_MAX_LENGTH = 2000
    DECK_NAME_MAX_LENGTH = 100
    DECK_DESCRIPTION_MAX_LENGTH = 500
    
    # Quality validation
    REVIEW_QUALITY_MIN = 1
    REVIEW_QUALITY_MAX = 5
    RESPONSE_TIME_MIN_SECONDS = 0
    RESPONSE_TIME_MAX_SECONDS = 3600  # 1 hour max

    # === STUDY SESSION CONFIGURATION ===
    DEFAULT_STUDY_SESSION_SIZE = 20
    MAX_STUDY_SESSION_SIZE = 50
    MIN_STUDY_SESSION_SIZE = 1
    
    # Due cards query limits
    DEFAULT_DUE_CARDS_LIMIT = 100
    MAX_DUE_CARDS_LIMIT = 100
    
    # Statistics
    DEFAULT_STATS_DATE_RANGE_DAYS = 30

    # === PERFORMANCE AND ANALYTICS ===
    # Analytics thresholds
    ANALYTICS_MIN_CARDS_FOR_INSIGHT = 3
    ANALYTICS_MASTERY_EASE_THRESHOLD = 2.8
    ANALYTICS_STRUGGLE_EASE_THRESHOLD = 2.2
    ANALYTICS_MASTERY_DIFFICULTY_THRESHOLD = 0.3
    ANALYTICS_STRUGGLE_DIFFICULTY_THRESHOLD = 0.7
    
    # Performance confidence
    ALGORITHM_BASE_CONFIDENCE = 0.8
    ALGORITHM_QUALITY_BONUS_MULTIPLIER = 0.03

    # === ANKI INTEGRATION ===
    ANKI_HOST = "localhost"
    ANKI_PORT = 8765
    ANKI_API_VERSION = 6
    ANKI_DEFAULT_NOTE_TYPE = "Basic"
    ANKI_CONNECTION_TIMEOUT = 10
    ANKI_SYNC_ENABLED_DEFAULT = True

    # === FILE AND DIRECTORY SETTINGS ===
    CONFIG_ENCODING = "utf-8"
    JSON_ENSURE_ASCII = False
    BACKUP_FILE_SUFFIX = ".bak"

    # === ERROR HANDLING ===
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 1
    
    # === LOGGING ===
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # === VERSION AND METADATA ===
    SYSTEM_VERSION = "1.0.0"
    API_VERSION = "v1"
    
    # Health check defaults
    HEALTH_CHECK_STATUS_HEALTHY = "healthy"
    HEALTH_CHECK_STATUS_UNHEALTHY = "unhealthy"

    @classmethod
    def get_database_path(cls, custom_path: str = None) -> Path:
        """Get the full database path, with optional override"""
        base_path = custom_path or cls.DATABASE_PATH
        return Path(base_path)

    @classmethod
    def get_algorithm_config(cls, algorithm_name: str) -> Dict[str, Any]:
        """Get configuration for a specific algorithm"""
        configs = {
            "sm2": {
                "default_ease_factor": cls.SM2_DEFAULT_EASE_FACTOR,
                "min_ease_factor": cls.SM2_MIN_EASE_FACTOR,
                "min_interval": cls.SM2_MIN_INTERVAL_DAYS,
                "max_interval": cls.SM2_MAX_INTERVAL_DAYS,
                "quality_min": cls.SM2_QUALITY_SCALE_MIN,
                "quality_max": cls.SM2_QUALITY_SCALE_MAX,
                "success_threshold": cls.SM2_SUCCESS_THRESHOLD,
            },
            "sm15": {
                "default_ease_factor": cls.SM15_DEFAULT_EASE_FACTOR,
                "min_ease": cls.SM15_MIN_EASE_FACTOR,
                "max_ease": cls.SM15_MAX_EASE_FACTOR,
                "min_interval": cls.SM15_MIN_INTERVAL_DAYS,
                "max_interval": cls.SM15_MAX_INTERVAL_DAYS,
                "default_difficulty": cls.SM15_DEFAULT_DIFFICULTY,
                "quality_min": cls.SM15_QUALITY_SCALE_MIN,
                "quality_max": cls.SM15_QUALITY_SCALE_MAX,
                "success_threshold": cls.SM15_SUCCESS_THRESHOLD,
            }
        }
        return configs.get(algorithm_name, configs["sm2"])

    @classmethod
    def get_validation_config(cls) -> Dict[str, Any]:
        """Get validation configuration for API endpoints"""
        return {
            "card_front_max_length": cls.CARD_FRONT_MAX_LENGTH,
            "card_back_max_length": cls.CARD_BACK_MAX_LENGTH,
            "deck_name_max_length": cls.DECK_NAME_MAX_LENGTH,
            "deck_description_max_length": cls.DECK_DESCRIPTION_MAX_LENGTH,
            "quality_min": cls.REVIEW_QUALITY_MIN,
            "quality_max": cls.REVIEW_QUALITY_MAX,
            "response_time_min": cls.RESPONSE_TIME_MIN_SECONDS,
            "response_time_max": cls.RESPONSE_TIME_MAX_SECONDS,
            "study_session_min": cls.MIN_STUDY_SESSION_SIZE,
            "study_session_max": cls.MAX_STUDY_SESSION_SIZE,
            "due_cards_limit_max": cls.MAX_DUE_CARDS_LIMIT,
        }

    @classmethod
    def get_anki_config(cls) -> Dict[str, Any]:
        """Get Anki integration configuration"""
        return {
            "host": cls.ANKI_HOST,
            "port": cls.ANKI_PORT,
            "api_version": cls.ANKI_API_VERSION,
            "default_note_type": cls.ANKI_DEFAULT_NOTE_TYPE,
            "timeout": cls.ANKI_CONNECTION_TIMEOUT,
            "enabled_default": cls.ANKI_SYNC_ENABLED_DEFAULT,
        }

    @classmethod
    def get_analytics_config(cls) -> Dict[str, Any]:
        """Get analytics and performance tracking configuration"""
        return {
            "min_cards_for_insight": cls.ANALYTICS_MIN_CARDS_FOR_INSIGHT,
            "mastery_ease_threshold": cls.ANALYTICS_MASTERY_EASE_THRESHOLD,
            "struggle_ease_threshold": cls.ANALYTICS_STRUGGLE_EASE_THRESHOLD,
            "mastery_difficulty_threshold": cls.ANALYTICS_MASTERY_DIFFICULTY_THRESHOLD,
            "struggle_difficulty_threshold": cls.ANALYTICS_STRUGGLE_DIFFICULTY_THRESHOLD,
        }

    @classmethod
    def is_valid_algorithm(cls, algorithm: str) -> bool:
        """Check if algorithm name is valid"""
        return algorithm in cls.AVAILABLE_ALGORITHMS

    @classmethod
    def is_valid_quality(cls, quality: int, algorithm: str = None) -> bool:
        """Check if quality score is valid for the given algorithm"""
        if algorithm == "sm15":
            return cls.SM15_QUALITY_SCALE_MIN <= quality <= cls.SM15_QUALITY_SCALE_MAX
        else:  # Default to SM2
            return cls.SM2_QUALITY_SCALE_MIN <= quality <= cls.SM2_QUALITY_SCALE_MAX


# Environment-based configuration overrides
def load_config_from_env():
    """Load configuration overrides from environment variables"""
    config_overrides = {}
    
    # Database path override
    if db_path := os.getenv("FLASHCARD_DB_PATH"):
        config_overrides["DATABASE_PATH"] = db_path
    
    # Algorithm override
    if algorithm := os.getenv("FLASHCARD_DEFAULT_ALGORITHM"):
        if FlashcardConfig.is_valid_algorithm(algorithm):
            config_overrides["DEFAULT_ALGORITHM"] = algorithm
    
    # Anki configuration
    if anki_host := os.getenv("ANKI_HOST"):
        config_overrides["ANKI_HOST"] = anki_host
        
    if anki_port := os.getenv("ANKI_PORT"):
        try:
            config_overrides["ANKI_PORT"] = int(anki_port)
        except ValueError:
            pass
    
    # Apply overrides to config class
    for key, value in config_overrides.items():
        setattr(FlashcardConfig, key, value)


# Load environment overrides on import
load_config_from_env()


# Convenience exports
DEFAULT_ALGORITHM = FlashcardConfig.DEFAULT_ALGORITHM
DATABASE_PATH = FlashcardConfig.DATABASE_PATH
VALIDATION_CONFIG = FlashcardConfig.get_validation_config()
ALGORITHM_CONFIG = FlashcardConfig.get_algorithm_config
ANKI_CONFIG = FlashcardConfig.get_anki_config()
ANALYTICS_CONFIG = FlashcardConfig.get_analytics_config()
