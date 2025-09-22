"""
Web module for the AI Module application.
Exports the web server functionality from the application.server module.
"""

from application.server.server import run_web_server

__all__ = ['run_web_server']