#!/usr/bin/env python3
"""
Installation verification script.

Checks that all components are properly installed and configured.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from loguru import logger


def check_python():
    """Check Python version."""
    import sys
    version = sys.version_info
    
    if version.major == 3 and version.minor >= 9:
        logger.success(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        logger.error(f"✗ Python {version.major}.{version.minor} (need 3.9+)")
        return False


def check_env():
    """Check environment variables."""
    if not os.path.exists('.env'):
        logger.error("✗ .env file not found")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key.startswith('your-'):
        logger.error("✗ OPENAI_API_KEY not set in .env")
        return False
    
    logger.success(f"✓ OPENAI_API_KEY configured ({api_key[:10]}...)")
    return True


def check_database():
    """Check database connection."""
    try:
        from src.config import config
        from sqlalchemy import create_engine, text
        
        engine = create_engine(config.DATABASE_URL)
        
        with engine.connect() as conn:
            # Test connection
            conn.execute(text("SELECT 1"))
            
            # Check pgvector
            try:
                conn.execute(text("SELECT '1'::vector"))
                logger.success("✓ Database connected with pgvector")
                return True
            except Exception as e:
                logger.error("✗ pgvector extension not installed")
                logger.info("  Install with: CREATE EXTENSION vector;")
                return False
                
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def check_tables():
    """Check database tables exist."""
    try:
        from src.config import config
        from sqlalchemy import create_engine, text
        
        engine = create_engine(config.DATABASE_URL)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            
            expected = ['observations', 'observation_cooccurrence', 'query_sessions']
            missing = [t for t in expected if t not in tables]
            
            if missing:
                logger.error(f"✗ Missing tables: {missing}")
                logger.info("  Run: python scripts/setup_database.py")
                return False
            else:
                logger.success(f"✓ All tables exist ({len(tables)} total)")
                return True
                
    except Exception as e:
        logger.error(f"✗ Table check failed: {e}")
        return False


def check_observations():
    """Check if observations are ingested."""
    try:
        from src.config import config
        from sqlalchemy import create_engine, text
        
        engine = create_engine(config.DATABASE_URL)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM observations"))
            count = result.scalar()
            
            if count == 0:
                logger.warning("⚠ No observations ingested")
                logger.info("  Run: python scripts/ingest_documents.py --limit 100")
                return False
            else:
                logger.success(f"✓ {count:,} observations in database")
                return True
                
    except Exception as e:
        logger.error(f"✗ Observation check failed: {e}")
        return False


def check_imports():
    """Check all required packages can be imported."""
    packages = [
        ('openai', 'OpenAI'),
        ('langchain', 'LangChain'),
        ('langgraph', 'LangGraph'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('pgvector', 'pgvector'),
        ('sentence_transformers', 'Sentence Transformers'),
        ('fastapi', 'FastAPI'),
    ]
    
    all_ok = True
    for module, name in packages:
        try:
            __import__(module)
            logger.success(f"✓ {name}")
        except ImportError:
            logger.error(f"✗ {name} not installed")
            all_ok = False
    
    return all_ok


def check_embeddings():
    """Check embedding generation works."""
    try:
        from src.utils.embeddings import get_embedding_generator
        
        gen = get_embedding_generator()
        embedding = gen.embed_text("test")
        
        if embedding is not None and len(embedding) > 0:
            logger.success(f"✓ Embeddings working (dim={len(embedding)})")
            return True
        else:
            logger.error("✗ Embedding generation failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Embedding check failed: {e}")
        return False


def check_tools():
    """Check retrieval tools work."""
    try:
        from src.config import config
        from sqlalchemy import create_engine
        from src.tools import RetrievalTools
        
        engine = create_engine(config.DATABASE_URL)
        tools = RetrievalTools(engine)
        
        # Try semantic search (even if no results)
        results = tools.semantic_search("test query", k=5)
        
        logger.success("✓ Retrieval tools working")
        return True
        
    except Exception as e:
        logger.error(f"✗ Tool check failed: {e}")
        return False


def main():
    """Run all checks."""
    print("\n" + "="*60)
    print("ECU INSTALLATION VERIFICATION")
    print("="*60 + "\n")
    
    checks = [
        ("Python Version", check_python),
        ("Environment Variables", check_env),
        ("Required Packages", check_imports),
        ("Database Connection", check_database),
        ("Database Tables", check_tables),
        ("Observations", check_observations),
        ("Embedding Generation", check_embeddings),
        ("Retrieval Tools", check_tools),
    ]
    
    results = {}
    for name, check_fn in checks:
        print(f"\n{name}:")
        try:
            results[name] = check_fn()
        except Exception as e:
            logger.error(f"✗ Check failed with exception: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60 + "\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. python main.py interactive")
        print("  2. python scripts/demo_queries.py")
        print("  3. python scripts/run_server.py")
    else:
        print("\n⚠️  Some checks failed. See errors above.")
        print("\nCommon fixes:")
        print("  • Database: python scripts/setup_database.py")
        print("  • Observations: python scripts/ingest_documents.py --limit 100")
        print("  • Packages: pip install -r requirements.txt")
        print("  • Environment: Check .env file has OPENAI_API_KEY")
    
    print()
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

