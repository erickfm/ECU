"""
Basic tests for ECU system components.
"""

import pytest
from sqlalchemy import create_engine
import tempfile
from pathlib import Path

from src.config import Config
from src.database import create_database, get_session, Observation
from src.utils.embeddings import EmbeddingGenerator
from src.tools import RetrievalTools


@pytest.fixture
def test_config():
    """Test configuration."""
    return Config(
        DATABASE_URL="sqlite:///test.db",
        OPENAI_API_KEY="test-key",
        USE_LOCAL_EMBEDDINGS=True,
    )


@pytest.fixture
def test_engine():
    """Create test database engine."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        engine = create_engine(f"sqlite:///{f.name}")
        yield engine


def test_embedding_generation():
    """Test embedding generation."""
    gen = EmbeddingGenerator(use_openai=False)
    
    text = "This is a test document."
    embedding = gen.embed_text(text)
    
    assert embedding is not None
    assert len(embedding) > 0
    assert embedding.shape[0] == gen.dimension


def test_observation_creation(test_engine):
    """Test creating observations."""
    session = get_session(test_engine)
    
    obs = Observation(
        doc_id="test_doc_1",
        context="This is a test observation",
        embedding=[0.1] * 384,
        metadata={"test": True}
    )
    
    session.add(obs)
    session.commit()
    
    # Retrieve
    retrieved = session.query(Observation).filter_by(doc_id="test_doc_1").first()
    assert retrieved is not None
    assert retrieved.context == "This is a test observation"
    
    session.close()


def test_semantic_search(test_engine):
    """Test semantic search tool."""
    session = get_session(test_engine)
    gen = EmbeddingGenerator(use_openai=False)
    
    # Create test observations
    texts = [
        "Jeffrey Epstein was investigated by the committee.",
        "The oversight committee reviewed financial records.",
        "Palm Beach police conducted searches.",
    ]
    
    for i, text in enumerate(texts):
        emb = gen.embed_text(text)
        obs = Observation(
            doc_id=f"doc_{i}",
            context=text,
            embedding=emb.tolist()
        )
        session.add(obs)
    
    session.commit()
    session.close()
    
    # Test search
    tools = RetrievalTools(test_engine)
    results = tools.semantic_search("investigation committee", k=2)
    
    assert len(results) > 0
    assert 'similarity' in results[0]


if __name__ == "__main__":
    pytest.main([__file__])

