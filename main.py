#!/usr/bin/env python3
"""
Main entry point for the ECU system.

Usage:
    python main.py query "Who approved transactions for Epstein?"
    python main.py interactive
"""

import sys
import argparse
import json
from pathlib import Path
from sqlalchemy import create_engine
from loguru import logger

from src.config import config
from src.agent import ECUAgent


def run_query(agent: ECUAgent, query: str):
    """Run a single query."""
    logger.info(f"Query: {query}")
    print("\n" + "="*80)
    print(f"QUERY: {query}")
    print("="*80 + "\n")
    
    result = agent.query(query)
    
    print("\n" + "-"*80)
    print("ANSWER:")
    print("-"*80)
    print(result.get('answer', 'No answer available'))
    
    print("\n" + "-"*80)
    print(f"CONFIDENCE: {result.get('confidence', 0.0):.2f}/10")
    print(f"ITERATIONS: {result.get('iterations', 0)}")
    print(f"OBSERVATIONS: {result.get('observations_count', 0)}")
    print("-"*80)
    
    if result.get('uncertainties'):
        print("\nUNCERTAINTIES:")
        for unc in result['uncertainties']:
            print(f"  - {unc}")
    
    if result.get('evidence_trail'):
        print("\nEVIDENCE TRAIL:")
        for step in result['evidence_trail']:
            print(f"  {step}")
    
    print("\n" + "="*80 + "\n")
    
    return result


def interactive_mode(agent: ECUAgent):
    """Run in interactive mode."""
    print("\n" + "="*80)
    print("ECU INTERACTIVE MODE")
    print("="*80)
    print("\nType your queries, or 'quit' to exit.\n")
    
    while True:
        try:
            query = input("Query> ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            run_query(agent, query)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description='Emergent Corpus Understanding System')
    parser.add_argument('mode', choices=['query', 'interactive'], help='Run mode')
    parser.add_argument('query_text', nargs='?', help='Query text (for query mode)')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    args = parser.parse_args()
    
    # Setup logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/ecu_{time}.log", rotation="100 MB")
    
    # Create engine
    logger.info("Initializing ECU system...")
    engine = create_engine(config.DATABASE_URL)
    
    # Create agent
    agent = ECUAgent(engine)
    logger.success("ECU system ready!")
    
    # Run
    if args.mode == 'query':
        if not args.query_text:
            print("Error: query text required in query mode")
            sys.exit(1)
        
        result = run_query(agent, args.query_text)
        
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2, default=str))
            logger.info(f"Results saved to {args.output}")
    
    else:  # interactive
        interactive_mode(agent)


if __name__ == "__main__":
    main()

