"""
FastAPI server for ECU system.

Phase 5: Production API with monitoring.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine
from loguru import logger

from src.config import config
from src.agent import ECUAgent
from src.database import QuerySession, get_session


# Models
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    max_iterations: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    session_id: str
    iterations: int
    observations_count: int
    uncertainties: List[str]
    evidence_trail: List[str]


class SessionStatus(BaseModel):
    session_id: str
    query: str
    status: str
    iterations: int
    confidence: Optional[float]
    created_at: datetime


# Create FastAPI app
app = FastAPI(
    title="ECU API",
    description="Emergent Corpus Understanding System API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
engine = None
agent = None


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup."""
    global engine, agent
    
    logger.info("Starting ECU API server...")
    
    engine = create_engine(config.DATABASE_URL)
    agent = ECUAgent(engine)
    
    logger.success("ECU API server ready!")


@app.get("/")
async def root():
    """Health check."""
    return {
        "status": "healthy",
        "service": "ECU API",
        "version": "1.0.0",
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, background_tasks: BackgroundTasks):
    """
    Execute a query against the corpus.
    
    Args:
        request: Query request with query text and optional session_id
        
    Returns:
        Query response with answer and evidence
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        logger.info(f"Received query: {request.query}")
        
        # Execute query
        result = agent.query(
            query=request.query,
            session_id=request.session_id
        )
        
        # Save session to database
        background_tasks.add_task(save_session, result, request.query)
        
        return QueryResponse(
            answer=result.get('answer', 'No answer available'),
            confidence=result.get('confidence', 0.0),
            session_id=result.get('session_id', ''),
            iterations=result.get('iterations', 0),
            observations_count=result.get('observations_count', 0),
            uncertainties=result.get('uncertainties', []),
            evidence_trail=result.get('evidence_trail', []),
        )
        
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions", response_model=List[SessionStatus])
async def list_sessions(limit: int = 10):
    """
    List recent query sessions.
    
    Args:
        limit: Maximum number of sessions to return
        
    Returns:
        List of session statuses
    """
    try:
        session = get_session(engine)
        
        sessions = session.query(QuerySession).order_by(
            QuerySession.created_at.desc()
        ).limit(limit).all()
        
        result = [
            SessionStatus(
                session_id=s.session_id,
                query=s.query,
                status=s.status,
                iterations=s.iterations,
                confidence=s.confidence_score,
                created_at=s.created_at,
            )
            for s in sessions
        ]
        
        session.close()
        return result
        
    except Exception as e:
        logger.error(f"Session list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str):
    """
    Get details of a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session details including state snapshot
    """
    try:
        session = get_session(engine)
        
        query_session = session.query(QuerySession).filter_by(
            session_id=session_id
        ).first()
        
        if not query_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        result = {
            "session_id": query_session.session_id,
            "query": query_session.query,
            "status": query_session.status,
            "iterations": query_session.iterations,
            "confidence": query_session.confidence_score,
            "answer": query_session.answer,
            "evidence_chain": query_session.evidence_chain,
            "state": query_session.state_snapshot,
            "created_at": query_session.created_at,
            "completed_at": query_session.completed_at,
        }
        
        session.close()
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """
    Get system statistics.
    
    Returns:
        Statistics about the system
    """
    try:
        from src.database import Observation
        
        session = get_session(engine)
        
        obs_count = session.query(Observation).count()
        session_count = session.query(QuerySession).count()
        
        recent_sessions = session.query(QuerySession).filter(
            QuerySession.status == 'completed'
        ).order_by(QuerySession.created_at.desc()).limit(10).all()
        
        avg_confidence = sum(s.confidence_score or 0 for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0
        avg_iterations = sum(s.iterations for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0
        
        session.close()
        
        return {
            "observations_count": obs_count,
            "sessions_count": session_count,
            "avg_confidence": round(avg_confidence, 2),
            "avg_iterations": round(avg_iterations, 1),
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def save_session(result: Dict, query: str):
    """Background task to save session to database."""
    try:
        session = get_session(engine)
        
        query_session = QuerySession(
            session_id=result.get('session_id'),
            query=query,
            status='completed',
            iterations=result.get('iterations', 0),
            confidence_score=result.get('confidence', 0.0),
            answer=result.get('answer'),
            evidence_chain=result.get('evidence_trail', []),
            state_snapshot={},
            completed_at=datetime.now(),
        )
        
        session.add(query_session)
        session.commit()
        session.close()
        
        logger.info(f"Saved session: {result.get('session_id')}")
        
    except Exception as e:
        logger.error(f"Session save error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

