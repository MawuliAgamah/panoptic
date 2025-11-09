"""FastAPI application package.

Exports the FastAPI `app` from `main.py`. The legacy `server.py` entrypoints
have been removed in favor of a single application instance.
"""

from .main import app  # noqa: F401

__all__ = ["app"]
