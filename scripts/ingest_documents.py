#!/usr/bin/env python3
"""
Ingestion script for processing documents into the observation store.

Usage:
    python scripts/ingest_documents.py [--limit N]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import create_engine

from src.config import config
from src.ingestion import DocumentProcessor


def main():
    parser = argparse.ArgumentParser(description='Ingest documents into observation store')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of files to process')
    parser.add_argument('--directory', type=str, default=None, help='Directory to process')
    args = parser.parse_args()
    
    # Get directory
    directory = Path(args.directory) if args.directory else config.DATA_DIR
    
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        sys.exit(1)
    
    logger.info(f"Starting ingestion from: {directory}")
    if args.limit:
        logger.info(f"Limiting to {args.limit} files")
    
    # Create engine
    engine = create_engine(config.DATABASE_URL)
    
    # Process documents
    processor = DocumentProcessor(engine)
    processor.process_directory(directory, limit=args.limit)
    
    logger.success("Ingestion complete!")


if __name__ == "__main__":
    main()

