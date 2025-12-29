"""
Database schema for the observation store.

Following the spec: PostgreSQL + pgvector for observation-first architecture.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, TIMESTAMP, 
    ForeignKey, Index, JSON, create_engine, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()


class Observation(Base):
    """
    Core table: Every mention, event, or document chunk is an observation.
    No entity resolution at storage time - keep maximum flexibility.
    """
    __tablename__ = "observations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(500), nullable=False, index=True)
    span_start = Column(Integer, nullable=True)
    span_end = Column(Integer, nullable=True)
    surface_form = Column(Text, nullable=True)  # e.g., "John", "the CEO", "J. Smith"
    context = Column(Text, nullable=False)  # Surrounding text / chunk content
    embedding = Column(Vector(1536), nullable=True)  # OpenAI embeddings are 1536-dimensional
    doc_timestamp = Column(TIMESTAMP, nullable=True, index=True)
    source_reliability = Column(Float, default=1.0)
    meta_data = Column(JSON, default={})  # Flexible additional data (renamed from metadata)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationships
    cooccurrences_a = relationship(
        "ObservationCooccurrence",
        foreign_keys="ObservationCooccurrence.obs_a_id",
        back_populates="observation_a"
    )
    cooccurrences_b = relationship(
        "ObservationCooccurrence",
        foreign_keys="ObservationCooccurrence.obs_b_id",
        back_populates="observation_b"
    )
    
    def __repr__(self):
        return f"<Observation(id={self.id}, doc_id={self.doc_id}, context={self.context[:50]}...)>"


class ObservationCooccurrence(Base):
    """
    Track co-occurrence relationships between observations.
    Enables relationship traversal without pre-computed entity graphs.
    """
    __tablename__ = "observation_cooccurrence"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    obs_a_id = Column(Integer, ForeignKey("observations.id"), nullable=False, index=True)
    obs_b_id = Column(Integer, ForeignKey("observations.id"), nullable=False, index=True)
    distance = Column(Integer, nullable=True)  # Words/characters apart
    doc_id = Column(String(500), nullable=False, index=True)
    co_occurrence_type = Column(String(50), nullable=True)  # 'same_sentence', 'same_paragraph', etc.
    strength = Column(Float, default=1.0)  # Weight based on proximity
    meta_data = Column(JSON, default={})
    
    # Relationships
    observation_a = relationship(
        "Observation",
        foreign_keys=[obs_a_id],
        back_populates="cooccurrences_a"
    )
    observation_b = relationship(
        "Observation",
        foreign_keys=[obs_b_id],
        back_populates="cooccurrences_b"
    )
    
    def __repr__(self):
        return f"<Cooccurrence(obs_a={self.obs_a_id}, obs_b={self.obs_b_id}, type={self.co_occurrence_type})>"


class CachedHypothesis(Base):
    """
    Optional: Cache high-confidence hypotheses for cross-query reuse.
    Start with session-only (Option 1), add this later (Option 2).
    """
    __tablename__ = "cached_hypotheses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    claim = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    evidence_obs_ids = Column(JSON, default=[])  # List of observation IDs
    contradicting_obs_ids = Column(JSON, default=[])
    query_context = Column(Text, nullable=True)
    corpus_version = Column(String(100), nullable=True)  # For invalidation
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_tested = Column(TIMESTAMP, default=datetime.utcnow)
    times_validated = Column(Integer, default=0)
    meta_data = Column(JSON, default={})
    
    def __repr__(self):
        return f"<CachedHypothesis(id={self.id}, claim={self.claim[:50]}..., confidence={self.confidence})>"


class QuerySession(Base):
    """
    Store query sessions for debugging and human-in-the-loop.
    Maps to LangGraph checkpointer concept.
    """
    __tablename__ = "query_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    query = Column(Text, nullable=False)
    status = Column(String(50), default="in_progress")  # in_progress, completed, failed
    iterations = Column(Integer, default=0)
    confidence_score = Column(Float, nullable=True)
    answer = Column(Text, nullable=True)
    evidence_chain = Column(JSON, default=[])
    state_snapshot = Column(JSON, default={})  # LangGraph state
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP, nullable=True)
    meta_data = Column(JSON, default={})
    
    def __repr__(self):
        return f"<QuerySession(id={self.id}, query={self.query[:50]}..., status={self.status})>"


# Indices for performance
Index("idx_obs_doc_id", Observation.doc_id)
Index("idx_obs_timestamp", Observation.doc_timestamp)
Index("idx_obs_surface_form", Observation.surface_form)
Index("idx_cooc_obs_a", ObservationCooccurrence.obs_a_id)
Index("idx_cooc_obs_b", ObservationCooccurrence.obs_b_id)
Index("idx_cooc_doc", ObservationCooccurrence.doc_id)
Index("idx_session_id", QuerySession.session_id)


def create_database(database_url: str):
    """
    Create database and tables with pgvector extension (if PostgreSQL).
    """
    from sqlalchemy import text
    
    engine = create_engine(database_url)
    
    # Enable pgvector extension (only for PostgreSQL)
    if 'postgresql' in database_url:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    return engine


def get_session(engine):
    """Get database session."""
    Session = sessionmaker(bind=engine)
    return Session()

