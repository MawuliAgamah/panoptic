#!/usr/bin/env python3
"""
Main entry point for the Knowledge Graph AI Module application.
Runs the unified application with modular web interface by default.

Usage:
    uv run main.py                    # Run full application (default)
    uv run main.py app                # Run full application  
    uv run main.py telegram           # Run only telegram bot
    uv run main.py process <file>     # Process a document
    uv run main.py query <terms>      # Query knowledge store
    uv run main.py test_flashcards    # Test flashcard system
"""

import sys
import os

# Add src to Python path to ensure imports work correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main application
from src.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())