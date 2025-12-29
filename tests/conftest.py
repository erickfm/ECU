"""
Shared test fixtures and configuration.

Auto-mocks heavy operations (embedding models, etc.) to ensure fast test runs.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


# ============================================================================
# Embedding Generator Mocks
# ============================================================================

@pytest.fixture
def mock_embedding_generator():
    """
    Mock EmbeddingGenerator to avoid loading 400MB Sentence Transformer model.
    Returns consistent 384-dimensional embeddings.
    """
    mock = Mock()
    mock.embed_text.return_value = np.random.rand(384).astype(np.float32)
    mock.embed_batch.return_value = lambda texts: [
        np.random.rand(384).astype(np.float32) for _ in texts
    ]
    mock.dimension = 384
    mock.use_openai = False
    return mock


@pytest.fixture(autouse=True)
def auto_mock_embeddings(monkeypatch):
    """
    Automatically mock embedding operations in all tests.
    This prevents the 400MB model from loading.
    """
    def fake_embed_text(self, text):
        # Use hash of text for reproducible embeddings in tests
        np.random.seed(hash(text) % 2**32)
        return np.random.rand(384).astype(np.float32)
    
    def fake_embed_batch(self, texts):
        return [fake_embed_text(self, t) for t in texts]
    
    # Patch the EmbeddingGenerator class methods
    monkeypatch.setattr(
        'src.utils.embeddings.EmbeddingGenerator.embed_text', 
        fake_embed_text
    )
    monkeypatch.setattr(
        'src.utils.embeddings.EmbeddingGenerator.embed_batch', 
        fake_embed_batch
    )
    
    # Also patch the global instance getter
    def fake_get_embedding_generator():
        mock = Mock()
        mock.embed_text = lambda text: fake_embed_text(mock, text)
        mock.embed_batch = lambda texts: fake_embed_batch(mock, texts)
        mock.dimension = 384
        mock.use_openai = False
        return mock
    
    monkeypatch.setattr(
        'src.utils.embeddings.get_embedding_generator',
        fake_get_embedding_generator
    )


@pytest.fixture(autouse=True)
def prevent_model_loading(monkeypatch):
    """
    Prevent SentenceTransformer from loading at import time.
    """
    class MockSentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name
        
        def encode(self, texts, **kwargs):
            return np.random.rand(len(texts), 384).astype(np.float32)
        
        def get_sentence_embedding_dimension(self):
            return 384
    
    monkeypatch.setattr(
        'sentence_transformers.SentenceTransformer',
        MockSentenceTransformer
    )


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def test_engine():
    """
    Create an in-memory SQLite database for testing.
    Uses StaticPool to allow multi-threaded access.
    
    Note: This creates a simplified schema compatible with SQLite
    (no pgvector types).
    """
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool
    )
    
    # Create simplified schema for SQLite (no Vector type)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                span_start INTEGER,
                span_end INTEGER,
                surface_form TEXT,
                context TEXT NOT NULL,
                embedding TEXT,
                doc_timestamp TIMESTAMP,
                source_reliability REAL DEFAULT 1.0,
                meta_data TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS observation_cooccurrence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obs_a_id INTEGER NOT NULL,
                obs_b_id INTEGER NOT NULL,
                distance INTEGER,
                doc_id TEXT NOT NULL,
                co_occurrence_type TEXT,
                strength REAL DEFAULT 1.0,
                meta_data TEXT DEFAULT '{}'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cached_hypotheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_obs_ids TEXT DEFAULT '[]',
                contradicting_obs_ids TEXT DEFAULT '[]',
                query_context TEXT,
                corpus_version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_tested TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                times_validated INTEGER DEFAULT 0,
                meta_data TEXT DEFAULT '{}'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS query_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                query TEXT NOT NULL,
                status TEXT DEFAULT 'in_progress',
                iterations INTEGER DEFAULT 0,
                confidence_score REAL,
                answer TEXT,
                evidence_chain TEXT DEFAULT '[]',
                state_snapshot TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                meta_data TEXT DEFAULT '{}'
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_obs_doc_id ON observations(doc_id)"))
        conn.commit()
    
    return engine


@pytest.fixture
def test_session(test_engine):
    """Get a test database session."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


# ============================================================================
# Configuration Fixtures  
# ============================================================================

@pytest.fixture(scope="session")
def test_config():
    """
    Test-specific configuration with reduced limits for fast test runs.
    """
    from src.config import Config
    return Config(
        DATABASE_URL="sqlite:///:memory:",
        OPENAI_API_KEY="test-key-not-used",
        MAX_ITERATIONS=3,
        SEMANTIC_SEARCH_K=5,
        CHUNK_SIZE=100,
        CHUNK_OVERLAP=10,
        MAX_OBSERVATIONS_IN_MEMORY=50,
        MAX_EVIDENCE_TRAIL_ITEMS=100,
    )


@pytest.fixture
def minimal_config():
    """Minimal config for unit tests."""
    from src.config import Config
    return Config(
        DATABASE_URL="sqlite:///:memory:",
        OPENAI_API_KEY="test-key",
        USE_LOCAL_EMBEDDINGS=True,
        MAX_ITERATIONS=2,
    )


# ============================================================================
# Mock LLM Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for agent tests."""
    mock_client = Mock()
    
    # Mock chat completions
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"sub_questions": []}'
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock embeddings
    mock_embedding_response = Mock()
    mock_embedding_response.data = [Mock()]
    mock_embedding_response.data[0].embedding = [0.1] * 1536
    mock_client.embeddings.create.return_value = mock_embedding_response
    
    return mock_client


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_observation(doc_id="test_doc", context="Test observation text"):
    """Helper to create test observation data."""
    return {
        'doc_id': doc_id,
        'context': context,
        'embedding': np.random.rand(384).tolist(),
        'meta_data': {'test': True}
    }


def create_test_observations(n=5):
    """Create multiple test observations."""
    return [
        create_test_observation(
            doc_id=f"doc_{i}",
            context=f"Test observation {i} content"
        )
        for i in range(n)
    ]

