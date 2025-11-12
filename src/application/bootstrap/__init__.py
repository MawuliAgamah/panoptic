"""Application composition root exports.

This module provides helpers to assemble the KnowledgeGraph client and related
services at application startup (FastAPI lifespan, CLI, workers, etc.).

It keeps wiring in the application layer so domain code remains framework‑agnostic.
"""

from .bootstrap import build_components, shutdown_components

__all__ = [
    "build_components",
    "shutdown_components",
]

