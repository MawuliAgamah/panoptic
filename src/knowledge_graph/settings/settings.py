"""Unified application settings for Knowledge Graph services.

This module defines a single Settings schema (with nested sections) and pure
loader utilities. It avoids import‑time side effects and global singletons.

Usage (composition root / FastAPI lifespan):
  from knowledge_graph.settings.settings import load_settings
  settings = load_settings()

Env convention:
  - Prefix: KG_
  - Nested sections use double underscore: __
  - Examples:
      KG_CORE__LOG_LEVEL=INFO
      KG_GRAPH_DB__DB_TYPE=sqlite
      KG_GRAPH_DB__DB_LOCATION=database/sql_lite/knowledgebase.db
      KG_CACHE_DB__DB_TYPE=sqlite
      KG_CACHE_DB__DB_LOCATION=database/sql_lite/cache.db
      KG_KB_STORE__BACKEND=sqlite
      KG_KB_STORE__LOCATION=database/sql_lite/knowledgebase.db
      KG_LLM__PROVIDER=openai
      KG_LLM__API_KEY=...
      KG_PIPELINE__ENABLE_PERSISTENCE=true
      KG_PIPELINE__CHUNK_SIZE=1000
      KG_FEATURES__CSV_PERSISTENCE_ENABLED=true
      KG_FEATURES__KB_DOCUMENT_MAPPING_ENABLED=true

Notes:
  - Do not instantiate Settings at import time. Use load_settings() or
    get_settings() from the application bootstrap only.
  - If LLM api key is not provided via KG_LLM__API_KEY, OPENAI_API_KEY is used
    as a fallback for convenience.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, MISSING
from functools import lru_cache
from typing import Any, Dict, Optional
import os


# ---------- Schema ----------

@dataclass
class CoreSettings:
    app_name: str = "KG Extract Backend"
    environment: str = "dev"  # dev|staging|prod
    log_level: str = "INFO"

@dataclass
class DBSettings:
    db_type: str = "sqlite"
    db_location: Optional[str] = "database/sql_lite/knowledgebase.db"



@dataclass
class GraphDBSettings:
    database_provider: Optional[str] = None
    host: Optional[str] = None 
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class KBStoreSettings:
    # sqlite | json | None (auto)
    backend: Optional[str] = None
    location: Optional[str] = None


@dataclass
class LLMSettings:
    provider: str = "openai"  # openai|ollama|none
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.2
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineSettings:
    enable_enrichment: bool = True
    enable_kg_extraction: bool = True
    enable_persistence: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunker_type: str = "auto"  # auto|regex|semantic


@dataclass
class FeaturesSettings:
    csv_persistence_enabled: bool = True
    kb_document_mapping_enabled: bool = True


@dataclass
class Settings:
    core: CoreSettings = field(default_factory=CoreSettings)
    db: DBSettings = field(default_factory=DBSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)

# ---------- Loader ----------


def _as_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in {"1", "true", "yes", "on"}


def _as_int(val: Any) -> int:
    if isinstance(val, int):
        return val
    return int(str(val).strip())


def _coerce(value: Any, target_type: Any) -> Any:
    """Coerce string envs into the dataclass field type where practical."""
    try:
        if target_type is bool:
            return _as_bool(value)
        if target_type is int:
            return _as_int(value)
        if target_type is float:
            return float(str(value).strip())
        # For Optional[...] we only check the origin param in the caller
        return value
    except Exception:
        return value


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _parse_prefixed_env(prefix: str = "KG_") -> Dict[str, Any]:
    """Collect environment variables with the given prefix and build a nested dict.

    Example: KG_GRAPH_DB__DB_TYPE=sqlite -> {"graph_db": {"db_type": "sqlite"}}
    """
    result: Dict[str, Any] = {}
    plen = len(prefix)
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        path = key[plen:]
        parts = [p for p in path.split("__") if p]
        if not parts:
            continue
        cursor = result
        for i, raw in enumerate(parts):
            k = raw.lower()
            if i == len(parts) - 1:
                cursor[k] = value
            else:
                cursor = cursor.setdefault(k, {})
    return result


def _instantiate_dataclass(cls: Any, data: Dict[str, Any]) -> Any:
    if not is_dataclass(cls):
        return data
    kwargs: Dict[str, Any] = {}
    for f in fields(cls):
        name = f.name
        t = f.type
        raw = (data or {}).get(name)

        # Optional[X] handling: try to detect common typing
        origin = getattr(t, "__origin__", None)
        args = getattr(t, "__args__", ())
        target_type = args[0] if origin is Optional and args else t

        if is_dataclass(target_type):
            # If raw is None or empty dict, use default_factory if available
            if raw is None or (isinstance(raw, dict) and not raw):
                # Try to get default_factory from field
                if hasattr(f, 'default_factory') and f.default_factory is not MISSING:
                    kwargs[name] = f.default_factory()
                else:
                    kwargs[name] = _instantiate_dataclass(target_type, {})
            else:
                kwargs[name] = _instantiate_dataclass(target_type, raw or {})
        else:
            if raw is None:
                # Try to get default from field
                if hasattr(f, 'default') and f.default is not MISSING:
                    kwargs[name] = f.default
                elif hasattr(f, 'default_factory') and f.default_factory is not MISSING:
                    kwargs[name] = f.default_factory()
                else:
                    kwargs[name] = None
            else:
                kwargs[name] = _coerce(raw, target_type)
    return cls(**kwargs)


def _normalize_env_settings(env: Dict[str, Any]) -> Dict[str, Any]:
    """Map env-derived keys (lowercase) to Settings dataclass structure."""
    # Already lowercased by _parse_prefixed_env
    # We accept KG_ENV / KG_CORE__ENVIRONMENT and KG_CORE__LOG_LEVEL shorthands
    core = env.get("core", {}).copy()
    if "env" in env:
        core.setdefault("environment", env.get("env"))
    if "log_level" in env:
        core.setdefault("log_level", env.get("log_level"))

    # Fallback LLM api key to OPENAI_API_KEY if not explicitly provided
    llm = env.get("llm", {}).copy()
    if not llm.get("api_key") and os.getenv("OPENAI_API_KEY"):
        llm["api_key"] = os.getenv("OPENAI_API_KEY")

    out: Dict[str, Any] = {
        "core": core,
        "db": env.get("db", {}),  # Add this line
        "graph_db": env.get("graph_db", {}),
        "cache_db": env.get("cache_db", {}),
        "kb_store": env.get("kb_store", {}),
        "llm": llm,
        "pipeline": env.get("pipeline", {}),
        "features": env.get("features", {}),
    }
    return out


def load_settings(overrides: Optional[Dict[str, Any]] = None) -> Settings:
    """Load settings from environment (KG_*), apply overrides, and return a Settings instance.

    This function does not mutate global state and performs no I/O beyond env reads.
    """
    # Start with defaults
    settings = Settings()
    
    # Load from environment
    env_data = _parse_prefixed_env(prefix="KG_")
    env_struct = _normalize_env_settings(env_data)
    
    # Apply environment overrides
    if env_struct.get("core"):
        for key, value in env_struct["core"].items():
            if hasattr(settings.core, key):
                setattr(settings.core, key, value)
    
    if env_struct.get("db"):
        for key, value in env_struct["db"].items():
            if hasattr(settings.db, key):
                setattr(settings.db, key, value)
    
    if env_struct.get("llm"):
        for key, value in env_struct["llm"].items():
            if hasattr(settings.llm, key):
                setattr(settings.llm, key, value)
    
    # Apply explicit overrides
    if overrides:
        if "core" in overrides:
            for key, value in overrides["core"].items():
                if hasattr(settings.core, key):
                    setattr(settings.core, key, value)
        if "db" in overrides:
            for key, value in overrides["db"].items():
                if hasattr(settings.db, key):
                    setattr(settings.db, key, value)
        if "llm" in overrides:
            for key, value in overrides["llm"].items():
                if hasattr(settings.llm, key):
                    setattr(settings.llm, key, value)
    
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor for settings when DI is not practical.

    Prefer calling load_settings() from your application bootstrap and passing
    the Settings instance explicitly to factories/builders.
    """
    return load_settings()


__all__ = [
    "CoreSettings",
    "DBSettings",
    "KBStoreSettings",
    "LLMSettings",
    "PipelineSettings",
    "FeaturesSettings",
    "Settings",
    "load_settings",
    "get_settings",
]

