#!/usr/bin/env python3
"""
Quick launcher for the unified AI Module application.
Run this to start everything at once.
"""

import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import run_unified_application

if __name__ == "__main__":
    print("🚀 Starting AI Module Application...")
    print("📍 This will start:")
    print("   • Web Interface (http://127.0.0.1:8000)")
    print("   • Knowledge Graph Backend")
    print("   • Flashcard System")
    print("   • Document Upload & Processing")
    print("   • Telegram Bot (if configured)")
    print("")
    print("Press Ctrl+C to stop")
    print("")

    asyncio.run(run_unified_application())