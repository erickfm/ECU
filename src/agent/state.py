"""
Agent state definitions for LangGraph.

Follows spec: query, sub_questions, observations, hypotheses, evidence_trail, 
iterations, confidence_score, answer.
"""

from typing import TypedDict, List, Dict, Optional, Annotated
from datetime import datetime
from operator import add


class SubQuestion(TypedDict):
    """A sub-question derived from the main query."""
    id: int
    text: str
    priority: str  # 'ESSENTIAL', 'CONDITIONAL', 'OPTIONAL'
    confidence: float
    status: str  # 'pending', 'in_progress', 'answered'


class Hypothesis(TypedDict):
    """A hypothesis about entities, relationships, or patterns."""
    id: int
    claim: str
    confidence: float
    evidence_ids: List[int]  # Observation IDs supporting this
    contradicting_ids: List[int]  # Observation IDs contradicting this
    relevant_to_subquestion: int  # Which sub-question does this help?
    impact_on_answer: str  # How does this affect the final answer?
    tested_at_iteration: int
    num_tests: int


class AgentState(TypedDict):
    """
    LangGraph state for the agent reasoning loop.
    
    This is the working memory during query execution.
    """
    # Core query
    query: str
    session_id: str
    
    # Query decomposition
    sub_questions: List[SubQuestion]
    
    # Evidence accumulation
    observations: Annotated[List[Dict], add]  # Accumulated observations
    
    # Hypothesis tracking
    hypotheses: List[Hypothesis]
    
    # Reasoning trace
    evidence_trail: Annotated[List[str], add]  # Human-readable reasoning steps
    
    # Iteration control
    iterations: int
    confidence_score: float
    stop_reason: Optional[str]
    
    # Output
    answer: Optional[str]
    uncertainties: List[str]
    
    # Metadata
    started_at: str  # ISO format timestamp
    tokens_used: int

