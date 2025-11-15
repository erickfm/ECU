#!/usr/bin/env python3
"""
Setup script for initializing the database.

Creates PostgreSQL database with pgvector extension and all tables.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.database import create_database
from src.config import config


def main():
    """Setup database."""
    logger.info(f"Setting up database: {config.DATABASE_URL}")
    
    try:
        engine = create_database(config.DATABASE_URL)
        logger.success("Database setup complete!")
        logger.info(f"Tables created: observations, observation_cooccurrence, cached_hypotheses, query_sessions")
        return engine
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

