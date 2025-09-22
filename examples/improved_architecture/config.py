"""Centralized configuration system"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    provider: str = "json"  # json, sqlite, postgresql, etc.
    path: str = "database/flashcards"
    connection_string: Optional[str] = None
    pool_size: int = 10
    timeout_seconds: int = 30


@dataclass
class AlgorithmConfig:
    """Algorithm configuration settings"""
    default_algorithm: str = "sm2"
    algorithms: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "sm2": {
            "default_ease_factor": 2.5,
            "minimum_ease_factor": 1.3,
            "ease_factor_bonus": 0.1,
            "ease_factor_penalty": 0.2
        },
        "sm15": {
            "default_ease_factor": 2.0,
            "difficulty_threshold": 0.7
        }
    })


@dataclass
class IntegrationConfig:
    """External integration settings"""
    anki_enabled: bool = False
    anki_connect_url: str = "http://localhost:8765"
    anki_deck_name: str = "Flashcards"

    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None

    web_api_enabled: bool = True
    web_api_host: str = "localhost"
    web_api_port: int = 8000


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 3


@dataclass
class FlashcardConfig:
    """Main configuration class"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    algorithms: AlgorithmConfig = field(default_factory=AlgorithmConfig)
    integrations: IntegrationConfig = field(default_factory=IntegrationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Application settings
    max_cards_per_session: int = 50
    default_session_limit: int = 20
    max_front_text_length: int = 500
    max_back_text_length: int = 2000
    max_deck_name_length: int = 100

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()

    def _validate_config(self):
        """Validate configuration values"""
        if self.max_cards_per_session < 1:
            raise ValueError("max_cards_per_session must be positive")

        if self.database.provider not in ["json", "sqlite", "postgresql"]:
            raise ValueError(f"Unsupported database provider: {self.database.provider}")

        if self.algorithms.default_algorithm not in self.algorithms.algorithms:
            raise ValueError(f"Default algorithm {self.algorithms.default_algorithm} not configured")


class ConfigManager:
    """Configuration manager with environment overrides and file loading"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._find_config_file()
        self._config: Optional[FlashcardConfig] = None

    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in standard locations"""
        possible_locations = [
            "flashcard_config.json",
            "config/flashcard_config.json",
            os.path.expanduser("~/.flashcards/config.json"),
            "/etc/flashcards/config.json"
        ]

        for location in possible_locations:
            if os.path.exists(location):
                return location
        return None

    def load_config(self) -> FlashcardConfig:
        """Load configuration from file and environment"""
        if self._config:
            return self._config

        # Start with defaults
        config_dict = {}

        # Load from file if exists
        if self.config_file and os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config_dict = json.load(f)

        # Apply environment overrides
        config_dict = self._apply_env_overrides(config_dict)

        # Create config object
        self._config = self._dict_to_config(config_dict)
        return self._config

    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        env_mappings = {
            "FLASHCARD_DB_PATH": ["database", "path"],
            "FLASHCARD_DB_PROVIDER": ["database", "provider"],
            "FLASHCARD_DEFAULT_ALGORITHM": ["algorithms", "default_algorithm"],
            "FLASHCARD_ANKI_ENABLED": ["integrations", "anki_enabled"],
            "FLASHCARD_ANKI_URL": ["integrations", "anki_connect_url"],
            "FLASHCARD_LOG_LEVEL": ["logging", "level"],
            "FLASHCARD_LOG_FILE": ["logging", "file_path"],
            "FLASHCARD_WEB_HOST": ["integrations", "web_api_host"],
            "FLASHCARD_WEB_PORT": ["integrations", "web_api_port"],
        }

        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate to nested dict and set value
                current = config_dict
                for key in path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Convert value to appropriate type
                final_value = self._convert_env_value(value)
                current[path[-1]] = final_value

        return config_dict

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment string to appropriate type"""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # Integer conversion
        if value.isdigit():
            return int(value)

        # Return as string
        return value

    def _dict_to_config(self, config_dict: Dict[str, Any]) -> FlashcardConfig:
        """Convert dictionary to FlashcardConfig object"""
        # Create nested dataclass objects
        database_config = DatabaseConfig(**config_dict.get("database", {}))
        algorithm_config = AlgorithmConfig(**config_dict.get("algorithms", {}))
        integration_config = IntegrationConfig(**config_dict.get("integrations", {}))
        logging_config = LoggingConfig(**config_dict.get("logging", {}))

        # Remove nested configs from main dict
        main_config = {k: v for k, v in config_dict.items()
                      if k not in ["database", "algorithms", "integrations", "logging"]}

        return FlashcardConfig(
            database=database_config,
            algorithms=algorithm_config,
            integrations=integration_config,
            logging=logging_config,
            **main_config
        )

    def save_config(self, config: FlashcardConfig, file_path: Optional[str] = None):
        """Save configuration to file"""
        file_path = file_path or self.config_file or "flashcard_config.json"

        config_dict = {
            "database": {
                "provider": config.database.provider,
                "path": config.database.path,
                "connection_string": config.database.connection_string,
                "pool_size": config.database.pool_size,
                "timeout_seconds": config.database.timeout_seconds
            },
            "algorithms": {
                "default_algorithm": config.algorithms.default_algorithm,
                "algorithms": config.algorithms.algorithms
            },
            "integrations": {
                "anki_enabled": config.integrations.anki_enabled,
                "anki_connect_url": config.integrations.anki_connect_url,
                "anki_deck_name": config.integrations.anki_deck_name,
                "telegram_enabled": config.integrations.telegram_enabled,
                "telegram_bot_token": config.integrations.telegram_bot_token,
                "web_api_enabled": config.integrations.web_api_enabled,
                "web_api_host": config.integrations.web_api_host,
                "web_api_port": config.integrations.web_api_port
            },
            "logging": {
                "level": config.logging.level,
                "format": config.logging.format,
                "file_path": config.logging.file_path,
                "max_file_size": config.logging.max_file_size,
                "backup_count": config.logging.backup_count
            },
            "max_cards_per_session": config.max_cards_per_session,
            "default_session_limit": config.default_session_limit,
            "max_front_text_length": config.max_front_text_length,
            "max_back_text_length": config.max_back_text_length,
            "max_deck_name_length": config.max_deck_name_length
        }

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2)


# Global configuration instance
_config_manager = ConfigManager()

def get_config() -> FlashcardConfig:
    """Get the global configuration instance"""
    return _config_manager.load_config()

def reload_config() -> FlashcardConfig:
    """Reload configuration from file/environment"""
    global _config_manager
    _config_manager._config = None
    return _config_manager.load_config()


# Configuration validation utilities
def validate_database_config(config: DatabaseConfig) -> None:
    """Validate database configuration"""
    if config.provider == "json":
        if not config.path:
            raise ValueError("JSON database requires path")
        # Ensure directory exists
        os.makedirs(os.path.dirname(config.path), exist_ok=True)

    elif config.provider in ["postgresql", "mysql"]:
        if not config.connection_string:
            raise ValueError(f"{config.provider} requires connection_string")


def setup_logging(config: LoggingConfig) -> None:
    """Setup logging based on configuration"""
    level = getattr(logging, config.level.upper())

    handlers = [logging.StreamHandler()]

    if config.file_path:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            config.file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format=config.format,
        handlers=handlers
    )