"""
Optimized tests for ECU system components.

NO HEAVY MODEL LOADING - Uses mocked embeddings from conftest.py.
All tests should run fast (<5 seconds total).
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


# ============================================================================
# Embedding Tests (using mocked embeddings from conftest.py autouse fixtures)
# ============================================================================

def test_embedding_generation(mock_embedding_generator):
    """Test embedding generation with mocked generator."""
    embedding = mock_embedding_generator.embed_text("test text")
    
    assert embedding is not None
    assert len(embedding) == 384
    assert embedding.dtype == np.float32


def test_embedding_batch(mock_embedding_generator):
    """Test batch embedding generation."""
    texts = ["text one", "text two", "text three"]
    embeddings = mock_embedding_generator.embed_batch(texts)
    
    assert callable(embeddings)  # Returns a lambda
    result = embeddings(texts)
    assert len(result) == 3
    for emb in result:
        assert len(emb) == 384


def test_embedding_dimension(mock_embedding_generator):
    """Test embedding dimension property."""
    assert mock_embedding_generator.dimension == 384


# ============================================================================
# Database Tests (using SQLite from conftest.py)
# ============================================================================

def test_observation_creation(test_engine):
    """Test creating observations in SQLite test database."""
    with test_engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO observations (doc_id, context, embedding)
            VALUES ('test_doc_1', 'This is a test observation', '[]')
        """))
        conn.commit()
        
        result = conn.execute(text("SELECT * FROM observations WHERE doc_id = 'test_doc_1'"))
        row = result.fetchone()
        
        assert row is not None
        assert row[1] == 'test_doc_1'  # doc_id
        assert row[5] == 'This is a test observation'  # context


def test_multiple_observations(test_engine):
    """Test creating and querying multiple observations."""
    with test_engine.connect() as conn:
        for i in range(5):
            conn.execute(text(f"""
                INSERT INTO observations (doc_id, context, embedding)
                VALUES ('doc_{i}', 'Observation content {i}', '[]')
            """))
        conn.commit()
        
        result = conn.execute(text("SELECT COUNT(*) FROM observations"))
        count = result.fetchone()[0]
        
        assert count == 5


def test_cooccurrence_creation(test_engine):
    """Test creating observation co-occurrences."""
    with test_engine.connect() as conn:
        # Create two observations first
        conn.execute(text("""
            INSERT INTO observations (doc_id, context) VALUES ('doc1', 'First observation')
        """))
        conn.execute(text("""
            INSERT INTO observations (doc_id, context) VALUES ('doc1', 'Second observation')
        """))
        
        # Create co-occurrence
        conn.execute(text("""
            INSERT INTO observation_cooccurrence (obs_a_id, obs_b_id, doc_id, co_occurrence_type, strength)
            VALUES (1, 2, 'doc1', 'adjacent_chunks', 1.0)
        """))
        conn.commit()
        
        result = conn.execute(text("SELECT * FROM observation_cooccurrence WHERE doc_id = 'doc1'"))
        row = result.fetchone()
        
        assert row is not None
        assert row[4] == 'doc1'  # doc_id


def test_query_session_creation(test_engine):
    """Test creating query sessions."""
    with test_engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO query_sessions (session_id, query, status)
            VALUES ('session_001', 'Test query', 'in_progress')
        """))
        conn.commit()
        
        result = conn.execute(text("""
            SELECT session_id, query, status FROM query_sessions 
            WHERE session_id = 'session_001'
        """))
        row = result.fetchone()
        
        assert row is not None
        assert row[0] == 'session_001'  # session_id
        assert row[1] == 'Test query'  # query
        assert row[2] == 'in_progress'  # status


# ============================================================================
# Configuration Tests
# ============================================================================

def test_config_defaults():
    """Test configuration default values."""
    from src.config import Config
    
    cfg = Config(
        DATABASE_URL="sqlite:///:memory:",
        OPENAI_API_KEY="test-key",
    )
    
    assert cfg.MAX_ITERATIONS > 0
    assert cfg.SEMANTIC_SEARCH_K > 0
    assert cfg.CHUNK_SIZE > 0


def test_config_memory_limits():
    """Test memory limit configuration values."""
    from src.config import Config
    
    cfg = Config(
        DATABASE_URL="sqlite:///:memory:",
        OPENAI_API_KEY="test-key",
        MAX_OBSERVATIONS_IN_MEMORY=50,
        MAX_EVIDENCE_TRAIL_ITEMS=100,
    )
    
    assert cfg.MAX_OBSERVATIONS_IN_MEMORY == 50
    assert cfg.MAX_EVIDENCE_TRAIL_ITEMS == 100


# ============================================================================
# Agent State Tests
# ============================================================================

def test_agent_state_creation():
    """Test agent state structure."""
    from src.agent.state import AgentState
    
    # AgentState is a TypedDict, so we can create it as a dict
    state = {
        'query': 'Test query',
        'session_id': 'test_session',
        'sub_questions': [],
        'observations': [],
        'hypotheses': [],
        'evidence_trail': [],
        'iterations': 0,
        'confidence_score': 0.0,
        'stop_reason': None,
        'answer': None,
        'uncertainties': [],
        'started_at': '2024-01-01T00:00:00',
        'tokens_used': 0,
    }
    
    assert state['query'] == 'Test query'
    assert state['iterations'] == 0
    assert len(state['observations']) == 0


def test_observation_accumulation():
    """Test that observations can accumulate in state."""
    state = {
        'observations': [],
        'evidence_trail': [],
    }
    
    # Simulate adding observations
    for i in range(10):
        state['observations'].append({
            'id': i,
            'doc_id': f'doc_{i}',
            'context': f'Observation {i}',
        })
    
    assert len(state['observations']) == 10
    assert state['observations'][5]['id'] == 5


def test_observation_pruning():
    """Test observation pruning logic."""
    MAX_OBS = 50
    
    state = {
        'observations': [],
        'evidence_trail': [],
    }
    
    # Add more than MAX_OBS observations
    for i in range(100):
        state['observations'].append({
            'id': i,
            'doc_id': f'doc_{i}',
            'context': f'Observation {i}',
        })
    
    # Apply pruning logic (as would be in workflow.py)
    if len(state['observations']) > MAX_OBS:
        state['observations'] = state['observations'][-MAX_OBS:]
        state['evidence_trail'].append(f"Pruned to {MAX_OBS} observations")
    
    assert len(state['observations']) == MAX_OBS
    assert state['observations'][0]['id'] == 50  # Should have kept last 50
    assert "Pruned to 50 observations" in state['evidence_trail']


# ============================================================================
# Utility Function Tests
# ============================================================================

def test_chunking_logic():
    """Test document chunking logic."""
    from src.ingestion.document_processor import DocumentProcessor
    from src.config import config
    
    # Create a mock engine (won't be used for chunking)
    mock_engine = Mock()
    
    with patch('src.ingestion.document_processor.get_embedding_generator'):
        processor = DocumentProcessor(mock_engine)
        processor.chunk_size = 20  # 20 words per chunk
        processor.chunk_overlap = 5
        
        # Generate text that exceeds MIN_OBSERVATION_LENGTH
        # Each "longword" is 8 chars, plus space = 9 chars per word
        # Need at least MIN_OBSERVATION_LENGTH (50) chars per chunk
        # So 20 words * ~9 chars = 180 chars per chunk (enough)
        text = "longword " * 100  # 100 words, ~900 chars
        chunks = processor._chunk_document(text.strip())
        
        assert len(chunks) > 0, f"Expected chunks but got none. MIN_OBS_LENGTH={config.MIN_OBSERVATION_LENGTH}"
        assert all('text' in chunk for chunk in chunks)
        assert all('start' in chunk for chunk in chunks)
        assert all('end' in chunk for chunk in chunks)
        
        # Verify chunk content
        for chunk in chunks:
            assert len(chunk['text']) >= config.MIN_OBSERVATION_LENGTH


def test_surface_form_extraction():
    """Test surface form extraction."""
    from src.ingestion.document_processor import DocumentProcessor
    
    mock_engine = Mock()
    
    with patch('src.ingestion.document_processor.get_embedding_generator'):
        processor = DocumentProcessor(mock_engine)
        
        text = "John Smith met with Jane Doe in New York."
        surface_forms = processor._extract_surface_forms(text)
        
        assert surface_forms is not None
        assert "John" in surface_forms
        assert "Smith" in surface_forms


# ============================================================================
# Integration Tests (with mocks)
# ============================================================================

def test_full_observation_pipeline(test_engine, mock_embedding_generator):
    """Test the full observation creation pipeline with mocks."""
    with test_engine.connect() as conn:
        # Simulate what DocumentProcessor would do
        doc_id = "test_document"
        context = "This is a test document about John Smith meeting with Jane Doe."
        embedding = mock_embedding_generator.embed_text(context)
        
        # Store observation
        conn.execute(text("""
            INSERT INTO observations (doc_id, context, embedding, surface_form)
            VALUES (:doc_id, :context, :embedding, :surface_form)
        """), {
            'doc_id': doc_id,
            'context': context,
            'embedding': str(embedding.tolist()),
            'surface_form': 'John, Smith, Jane, Doe'
        })
        conn.commit()
        
        # Verify retrieval
        result = conn.execute(text("SELECT * FROM observations WHERE doc_id = :doc_id"), 
                             {'doc_id': doc_id})
        row = result.fetchone()
        
        assert row is not None
        assert 'John Smith' in row[5]  # context


def test_semantic_search_mock():
    """Test semantic search with fully mocked components."""
    # This tests the search logic without actual database or embeddings
    
    query_embedding = np.random.rand(384).astype(np.float32)
    
    # Mock observations with embeddings
    observations = [
        {
            'id': 1,
            'doc_id': 'doc_1',
            'context': 'Investigation committee met.',
            'embedding': np.random.rand(384).astype(np.float32)
        },
        {
            'id': 2,
            'doc_id': 'doc_2',
            'context': 'Financial records reviewed.',
            'embedding': np.random.rand(384).astype(np.float32)
        },
    ]
    
    # Calculate cosine similarities (simplified)
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    results = []
    for obs in observations:
        sim = cosine_similarity(query_embedding, obs['embedding'])
        results.append({
            'observation': obs,
            'similarity': float(sim)
        })
    
    # Sort by similarity
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    assert len(results) == 2
    assert 'similarity' in results[0]
    assert results[0]['similarity'] >= results[1]['similarity']


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
