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
from pathlib import Path

# IMPORTANT: Setup DSPy cache before any DSPy imports to avoid permission errors
def setup_dspy_cache():
    """Setup DSPy cache directory to avoid permission errors"""
    try:
        # Option 1: Use project-local cache
        project_root = Path(__file__).parent
        cache_dir = project_root / '.cache' / 'dspy'
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ['DSPY_CACHEDIR_ROOT'] = str(cache_dir)
        print(f"DSPy cache directory set to: {cache_dir}")
        
    except Exception as e:
        # Option 2: Use user home cache
        try:
            home_cache = Path.home() / '.cache' / 'dspy'
            home_cache.mkdir(parents=True, exist_ok=True)
            os.environ['DSPY_CACHEDIR_ROOT'] = str(home_cache)
            print(f"Using home cache directory: {home_cache}")
            
        except Exception as e2:
            # Option 3: Disable caching entirely
            os.environ['DSPY_CACHE_DISABLED'] = '1'
            print("Could not create cache directory, disabled DSPy caching")

# Setup DSPy cache before any imports
setup_dspy_cache()

# Add src to Python path to ensure imports work correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main application
from src.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())