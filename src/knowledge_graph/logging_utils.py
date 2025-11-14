"""Logging context utilities for injecting document/run IDs into log records and configuring logging."""

from __future__ import annotations

import logging
import contextvars
import os
from typing import Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Context variables to carry correlation IDs across the pipeline execution
_doc_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("doc_id", default="-")
_run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="-")


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


class ContextFormatter(logging.Formatter):
    """Custom formatter that only shows doc= and run= when they're not "-".
    
    Supports ANSI color codes in log messages for console output.
    """
    
    def __init__(self, use_colors: bool = True):
        """Initialize formatter.
        
        Args:
            use_colors: If True, preserve ANSI color codes in output (for console).
                       If False, strip color codes (for file output).
        """
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        # Get the base formatted message
        base_format = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        
        # Check if doc_id and run_id are set and not "-"
        doc_id = getattr(record, 'doc_id', '-')
        run_id = getattr(record, 'run_id', '-')
        
        # Build context string only if values are meaningful
        context_parts = []
        if doc_id and doc_id != '-':
            context_parts.append(f'doc={doc_id}')
        if run_id and run_id != '-':
            context_parts.append(f'run={run_id}')
        
        # Add context to format if present
        if context_parts:
            context_str = ' '.join(context_parts)
            format_str = f'%(asctime)s | %(levelname)s | %(name)s | {context_str} | %(message)s'
        else:
            format_str = base_format
        
        # Create a temporary formatter with the dynamic format
        temp_formatter = logging.Formatter(format_str)
        formatted = temp_formatter.format(record)
        
        # Strip ANSI codes if colors are disabled (for file output)
        if not self.use_colors:
            import re
            ansi_escape = re.compile(r'\033\[[0-9;]*m')
            formatted = ansi_escape.sub('', formatted)
        
        return formatted


class InjectContextFilter(logging.Filter):
    """Logging filter that injects document and run IDs into every record."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        # Attach correlation fields if missing so formatters can include them safely
        if not hasattr(record, "doc_id"):
            try:
                record.doc_id = _doc_id_var.get()
            except Exception:
                record.doc_id = "-"
        if not hasattr(record, "run_id"):
            try:
                record.run_id = _run_id_var.get()
            except Exception:
                record.run_id = "-"
        return True


def set_logging_context(doc_id: Optional[str], run_id: Optional[str]) -> None:
    """Set logging correlation context for current execution."""
    _doc_id_var.set(doc_id or "-")
    _run_id_var.set(run_id or "-")


def clear_logging_context() -> None:
    """Clear logging correlation context."""
    _doc_id_var.set("-")
    _run_id_var.set("-")


def red(text: str) -> str:
    """Wrap text with red ANSI color code."""
    return f"{Colors.RED}{text}{Colors.RESET}"


def green(text: str) -> str:
    """Wrap text with green ANSI color code."""
    return f"{Colors.GREEN}{text}{Colors.RESET}"


def yellow(text: str) -> str:
    """Wrap text with yellow ANSI color code."""
    return f"{Colors.YELLOW}{text}{Colors.RESET}"


def blue(text: str) -> str:
    """Wrap text with blue ANSI color code."""
    return f"{Colors.BLUE}{text}{Colors.RESET}"


def bold(text: str) -> str:
    """Wrap text with bold ANSI code."""
    return f"{Colors.BOLD}{text}{Colors.RESET}"


def setup_logging(project_root: Optional[Path] = None) -> None:
    """Configure root logger with consistent formatting and handlers.
    
    This ensures all child loggers inherit the same configuration.
    Call this early in your application startup, before any other imports that create loggers.
    
    Args:
        project_root: Optional path to project root. If not provided, will try to infer from
                     common locations or use current working directory.
    """
    try:
        # Get root logger - all child loggers inherit from this
        root_logger = logging.getLogger()
        
        # Only configure if not already configured (avoid duplicate handlers)
        if root_logger.handlers:
            return
        
        root_logger.setLevel(logging.INFO)
        # Ensure child loggers propagate to root (default, but explicit is better)
        root_logger.propagate = True

        # Compute logs path; honor KG_LOG_FILE if provided
        log_file_env = os.getenv('KG_LOG_FILE')
        if log_file_env:
            log_path = Path(log_file_env)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = log_path
        else:
            # Try to infer project root if not provided
            if project_root is None:
                # Try common locations: look for .git, pyproject.toml, or setup.py
                current = Path.cwd()
                for parent in [current] + list(current.parents):
                    if any((parent / marker).exists() for marker in ['.git', 'pyproject.toml', 'setup.py']):
                        project_root = parent
                        break
                else:
                    # Fallback to current working directory
                    project_root = current
            
            logs_dir = project_root / 'logs'
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / 'app.log'

        # Use custom formatter with colors for console, without colors for file
        console_formatter = ContextFormatter(use_colors=True)
        file_formatter = ContextFormatter(use_colors=False)

        # Console handler (with colors)
        ch = logging.StreamHandler()
        ch.setFormatter(console_formatter)
        ch.addFilter(InjectContextFilter())
        root_logger.addHandler(ch)

        # File handler (without colors)
        fh = RotatingFileHandler(str(log_file), maxBytes=10_000_000, backupCount=5, encoding='utf-8')
        fh.setFormatter(file_formatter)
        fh.addFilter(InjectContextFilter())
        root_logger.addHandler(fh)
        
        # Log that logging is configured
        logger = logging.getLogger(__name__)
        logger.info("Logging configured - all child loggers will inherit this configuration")
        
    except Exception as e:
        # Fall back to basic config without context if needed
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
        logging.getLogger(__name__).warning(f"Failed to setup advanced logging: {e}")

