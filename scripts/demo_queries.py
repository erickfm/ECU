#!/usr/bin/env python3
"""
Demo script showing example queries on the Epstein oversight documents.

Usage:
    python scripts/demo_queries.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from loguru import logger

from src.config import config
from src.agent import ECUAgent


def run_demo():
    """Run demo queries."""
    
    # Example queries progressing from simple to complex
    queries = [
        # Simple (1-hop)
        {
            "query": "Who is Jeffrey Epstein?",
            "description": "Simple factual query - should be answered in 1-2 iterations"
        },
        
        # Medium (2-3 hop)
        {
            "query": "What organizations or entities are mentioned in connection with Epstein?",
            "description": "Medium complexity - requires gathering mentions across documents"
        },
        
        # Hard (multi-hop, implicit)
        {
            "query": "What patterns emerge about how the oversight committee investigated Epstein?",
            "description": "Hard - requires identifying implicit patterns across many documents"
        },
        
        # Very hard (emergent understanding)
        {
            "query": "Are there any contradictions in how different documents describe Epstein's activities?",
            "description": "Very hard - requires finding conflicting information and explaining discrepancies"
        },
    ]
    
    print("\n" + "="*80)
    print("ECU SYSTEM DEMO")
    print("Dataset: House Oversight Documents on Jeffrey Epstein")
    print("="*80 + "\n")
    
    # Create agent
    logger.info("Initializing ECU agent...")
    engine = create_engine(config.DATABASE_URL)
    agent = ECUAgent(engine)
    logger.success("Agent ready!")
    
    # Run each query
    for i, query_info in enumerate(queries, 1):
        query = query_info['query']
        description = query_info['description']
        
        print(f"\n{'='*80}")
        print(f"QUERY {i}/{len(queries)}")
        print(f"{'='*80}")
        print(f"Query: {query}")
        print(f"Expected: {description}")
        print(f"{'-'*80}\n")
        
        try:
            result = agent.query(query)
            
            print("ANSWER:")
            print(result.get('answer', 'No answer available'))
            
            print(f"\nMETRICS:")
            print(f"  Confidence: {result.get('confidence', 0.0):.2f}/10")
            print(f"  Iterations: {result.get('iterations', 0)}")
            print(f"  Observations: {result.get('observations_count', 0)}")
            
            if result.get('uncertainties'):
                print(f"\nUNCERTAINTIES:")
                for unc in result['uncertainties']:
                    print(f"  - {unc}")
            
            print(f"\nEVIDENCE TRAIL:")
            for step in result.get('evidence_trail', [])[:5]:  # Show first 5 steps
                print(f"  {step}")
            if len(result.get('evidence_trail', [])) > 5:
                print(f"  ... and {len(result['evidence_trail']) - 5} more steps")
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            print(f"ERROR: {e}")
    
    print(f"\n{'='*80}")
    print("DEMO COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    run_demo()

