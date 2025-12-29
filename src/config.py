"""
Configuration management for ECU system.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

class Config(BaseModel):
    """System configuration."""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://localhost:5432/ecu_db"
    )
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Sentence Transformers (fallback)
    SENTENCE_TRANSFORMER_MODEL: str = os.getenv(
        "SENTENCE_TRANSFORMER_MODEL",
        "all-MiniLM-L6-v2"
    )
    
    # Paths
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "/Users/erick/Downloads/all-ocr-text"))
    LOG_DIR: Path = Path("logs")
    CACHE_DIR: Path = Path("data/cache")
    
    # Agent Settings
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "15"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "100000"))
    MAX_TIME_SECONDS: int = int(os.getenv("MAX_TIME_SECONDS", "60"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.8"))
    MIN_CONFIDENCE_CONTINUE: float = float(os.getenv("MIN_CONFIDENCE_CONTINUE", "0.5"))
    
    # Retrieval Settings
    SEMANTIC_SEARCH_K: int = int(os.getenv("SEMANTIC_SEARCH_K", "20"))
    COOCCURRENCE_WINDOW: int = int(os.getenv("COOCCURRENCE_WINDOW", "100"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    
    # Observation Settings
    MIN_OBSERVATION_LENGTH: int = int(os.getenv("MIN_OBSERVATION_LENGTH", "50"))
    MAX_OBSERVATION_LENGTH: int = int(os.getenv("MAX_OBSERVATION_LENGTH", "1000"))
    
    # Memory Management Limits (prevents OOM on long sessions)
    MAX_OBSERVATIONS_IN_MEMORY: int = int(os.getenv("MAX_OBSERVATIONS_IN_MEMORY", "100"))
    MAX_EVIDENCE_TRAIL_ITEMS: int = int(os.getenv("MAX_EVIDENCE_TRAIL_ITEMS", "200"))
    MAX_HYPOTHESES: int = int(os.getenv("MAX_HYPOTHESES", "50"))
    OBSERVATION_CONTEXT_LIMIT: int = int(os.getenv("OBSERVATION_CONTEXT_LIMIT", "500"))
    
    # Ingestion Settings
    INGESTION_SUB_BATCH_SIZE: int = int(os.getenv("INGESTION_SUB_BATCH_SIZE", "10"))
    INGESTION_FLUSH_THRESHOLD: int = int(os.getenv("INGESTION_FLUSH_THRESHOLD", "500"))
    
    # Use local embeddings (avoids OpenAI calls in tests)
    USE_LOCAL_EMBEDDINGS: bool = os.getenv("USE_LOCAL_EMBEDDINGS", "false").lower() == "true"
    
    class Config:
        arbitrary_types_allowed = True

# Global config instance
config = Config()

