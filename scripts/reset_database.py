#!/usr/bin/env python3
"""Utility script to drop all tables and recreate the database schema.

Usage:
    python scripts/reset_database.py
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from knowledge_graph.settings.settings import load_settings
from knowledge_graph.persistence.sqlite.sql_lite import SqlLite


def main():
    """Drop all tables and recreate schema."""
    print("Loading settings...")
    settings = load_settings()
    
    print(f"Database path: {settings.db.db_location}")
    
    # Create SqlLite instance
    sql_lite = SqlLite(settings)
    
    # Drop all tables (or delete file entirely)
    print("\n⚠️  Dropping all tables...")
    # Use delete_file=True to completely remove the database file for a clean start
    sql_lite.drop_all_tables(delete_file=True)
    
    # Recreate tables
    print("\n📦 Creating fresh tables...")
    sql_lite.create_tables()
    
    print("\n✅ Database reset complete!")


if __name__ == "__main__":
    main()

