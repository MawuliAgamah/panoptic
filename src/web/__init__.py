"""
Web module for the AI Module application.
If you need to reference the FastAPI app, import it from application.api.main.
"""

from application.api.main import app as web_app  # pragma: no cover

__all__ = ["web_app"]
