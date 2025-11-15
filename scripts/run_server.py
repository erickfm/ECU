#!/usr/bin/env python3
"""
Run the ECU API server.

Usage:
    python scripts/run_server.py [--host 0.0.0.0] [--port 8000]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description='Run ECU API server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    args = parser.parse_args()
    
    logger.info(f"Starting ECU API server on {args.host}:{args.port}")
    
    uvicorn.run(
        "src.api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()

