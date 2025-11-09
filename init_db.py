#!/usr/bin/env python3
"""
Script to initialize the SQLite database with all tables.
"""

import asyncio
from app.core.database import init_db
from app.models import *  # Import all models to register them with Base metadata

async def main():
    """Initialize the database."""
    print("Initializing SQLite database...")
    
    # Create all tables
    await init_db()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())