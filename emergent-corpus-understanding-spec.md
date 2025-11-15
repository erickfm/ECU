# Emergent Corpus Understanding System: Project Specification

## Executive Summary

Build a system that develops **emergent understanding** of large, messy corpora—comparable to a domain expert who has lived with material for years—and uses that understanding to answer questions, generate hypotheses, and explain patterns that no single source contains.

This system addresses a fundamental gap: most current systems treat documents as independent retrieval sources, but many important insights are **distributed**, **emergent**, **implicit**, **inductive**, and **provable** only through evidence chains across hundreds or thousands of sources.

## Core Philosophy

### The Observation-First Principle

**Key Insight**: Don't pre-compute entities or world-models. Keep observations as the primary substrate and let patterns emerge **during query execution**.

Think of it like this: A human expert reading through thousands of documents doesn't maintain a perfect, consistent knowledge graph in their head. They maintain fuzzy awareness of the corpus, and when asked a specific question, they mentally traverse what they've read, patterns crystallize *in the context of that question*, and connections emerge through the act of inquiry.

**"Writing is thinking" applied to corpus understanding**: The system doesn't understand the corpus until it tries to answer a question. The reasoning process IS the pattern discovery process.

### Why This Matters

Traditional approaches fail because they force premature commitment:
- **Pre-built knowledge graphs**: Rigid entity boundaries, contradictions get "resolved" away
- **Standard RAG**: No multi-step reasoning, no entity understanding
- **Long-context models**: No revisable beliefs, no persistent structure

Our approach:
- **Flexible boundaries**: "John" and "J. Smith" might cluster for one query, separate for another
- **Preserved contradictions**: Doc A says X, Doc B says Y—both remain visible
- **Evidence-grounded**: Every conclusion traces to specific observations
- **Query-adapted**: Entity resolution happens in service of answering a specific question

## Problem Statement

### What We're Building

Given a **large, heterogeneous corpus** (documents, logs, tables, structured records) and **queries that arrive over time**, the system should:

1. **Maintain a rich observation store** with multiple indices (semantic, co-occurrence, temporal, graph)
2. **Execute query-time reasoning** that dynamically explores the observation space
3. **Form and test hypotheses** about entities, relationships, and patterns
4. **Accumulate evidence** across multiple reasoning steps
5. **Synthesize answers** with explicit evidence chains and uncertainty quantification

### Five Key Properties

Target insights with ALL of these characteristics:

1. **Distributed**: Information scattered across many artifacts, often across time and modalities
2. **Emergent**: Pattern visible only when considering many pieces together
3. **Implicit**: Never explicitly stated, must be inferred from correlations, absences, structural regularities
4. **Inductive**: Must generalize to new entities and pattern combinations not seen during training
5. **Provable**: Conclusions must trace back to specific documents/spans/events for human audit

### Example Domains

- **Investigative journalism**: Scandal networks from flight logs, emails, financial records
- **Software engineering**: Codebase evolution from commits, docs, logs
- **Scientific research**: Concept lineages across papers and datasets
- **System operations**: Failure patterns across distributed traces
- **Legal discovery**: Case relationships across statutes, precedents, filings

## Technical Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Query Interface                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Reasoning Loop (LangGraph)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Query Decomposition                               │   │
│  │ 2. Observation Gathering (tool calls)                │   │
│  │ 3. Pattern Detection                                 │   │
│  │ 4. Hypothesis Formation & Testing                    │   │
│  │ 5. Iteration Control & Meta-Reasoning                │   │
│  │ 6. Evidence Synthesis                                │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 Tool Layer (Database Queries)               │
│  • semantic_search()      • find_cooccurrences()            │
│  • temporal_query()       • traverse_graph()                │
│  • cluster_observations() • find_contradictions()           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Observation Store                         │
│  ┌──────────────┬────────────────┬──────────────────────┐   │
│  │ Observations │ Vector Index   │ Co-occurrence Graph  │   │
│  │ (Raw Data)   │ (Semantic)     │ (Relationships)      │   │
│  ├──────────────┼────────────────┼──────────────────────┤   │
│  │ Temporal     │ Metadata       │ Source Reliability   │   │
│  │ Index        │ (JSONB)        │ Scores               │   │
│  └──────────────┴────────────────┴──────────────────────┘   │
│         PostgreSQL + pgvector (or similar)                   │
└─────────────────────────────────────────────────────────────┘
```

### Storage Layer: The Observation Store

**Design Principle**: Every mention, event, or document chunk is an **observation**—a concrete, grounded thing that was said, written, or recorded.

**Schema (Conceptual)**:
```sql
-- Primary table: every observation
CREATE TABLE observations (
    id SERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,              -- Source document
    span_start INT,                     -- Location in doc
    span_end INT,
    surface_form TEXT,                  -- "John", "the CEO", "J. Smith"
    context TEXT,                       -- Surrounding text
    embedding VECTOR(768),              -- Semantic representation
    doc_timestamp TIMESTAMP,            -- When was this created/recorded
    source_reliability FLOAT,           -- Trust score
    metadata JSONB                      -- Flexible additional data
);

-- Co-occurrence tracking
CREATE TABLE observation_cooccurrence (
    obs_a_id INT REFERENCES observations(id),
    obs_b_id INT REFERENCES observations(id),
    distance INT,                       -- Words/sentences apart
    doc_id TEXT,
    co_occurrence_type TEXT,            -- 'same_sentence', 'same_paragraph', etc.
    PRIMARY KEY (obs_a_id, obs_b_id, doc_id)
);

-- Indices
CREATE INDEX ON observations USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON observations (surface_form);
CREATE INDEX ON observations (doc_timestamp);
CREATE INDEX ON observations USING gin (metadata);
CREATE INDEX ON observation_cooccurrence (obs_a_id);
CREATE INDEX ON observation_cooccurrence (obs_b_id);
```

**Key Properties**:
- No entity resolution at storage time
- Multiple observations can refer to the same underlying entity without being merged
- Rich indices enable different traversal strategies
- Metadata allows domain-specific extensions without schema changes

**Technology Options**:
- **PostgreSQL + pgvector**: Single system, good performance, mature, handles both structured and vector data
- **Qdrant/Weaviate + PostgreSQL**: Specialized vector DB + relational DB (more complex but potentially better at scale)
- **Neo4j + Vector DB**: If graph traversal becomes the dominant operation

**Recommendation**: Start with PostgreSQL + pgvector. It's simpler, performs well up to 10-100M observations, and avoids managing multiple systems. Migrate only if proven necessary.

### Agent Layer: Query-Time Reasoning

**Design Principle**: The agent is a **goal-directed exploration system** over the observation space. It doesn't have a pre-computed answer—it discovers it through iterative reasoning.

#### Core Loop

```
WHILE not done AND iterations < max_iterations:
    1. Meta-reasoning: "Can I answer the query now? What's my confidence?"
    2. If confidence > threshold: SYNTHESIZE and STOP
    3. Identify: "What uncertainty blocks me from answering?"
    4. Plan: "What evidence would reduce that uncertainty?"
    5. Execute: Use tools to gather that evidence
    6. Update: Revise hypothesis confidences based on new observations
    7. iterations++

SYNTHESIZE answer with evidence chains
```

#### Components

**1. Query Decomposition**
- Input: User query
- Output: 2-5 sub-questions with priority ranking
- Purpose: Break complex queries into tractable pieces
- Each sub-question is a "goal" that guides exploration

Example:
```
Query: "Who approved transaction T?"

Sub-questions:
1. What is transaction T? (ESSENTIAL, confidence: 0%)
2. Who are potential approvers? (ESSENTIAL, confidence: 0%)
3. Which approvers acted on T? (ESSENTIAL, confidence: 0%)
4. Are there coreferences? (CONDITIONAL, confidence: 0%)
   - Only matters if multiple approvers found
```

**2. Observation Gathering**
- Tools: semantic_search, find_cooccurrences, temporal_query, traverse_graph, cluster_observations
- Strategy: LLM decides which tools to use based on current hypothesis state
- Evidence accumulation: Each tool call adds observations to working memory

**3. Pattern Detection**
- Input: Accumulated observations
- Output: Provisional hypotheses with confidence scores
- Process: LLM reads observations and identifies:
  - Potential coreferences ("John" ~ "J. Smith")
  - Temporal patterns
  - Contradictions
  - Relationships

**4. Hypothesis Formation & Testing**
- Structure: `{claim, confidence, evidence_ids, relevant_to_subquestion_id}`
- Lifecycle: Formed → Tested → Strengthened/Weakened → Accepted/Rejected
- Constraint: **Every hypothesis must link to a sub-question**

**5. Iteration Control**

**The Hard Problem**: When to stop exploring?

**Multi-layered approach**:

a) **Hard limits** (safety):
   - Max iterations: 10-15
   - Max tokens: 100K
   - Max time: 60 seconds
   - Whichever hits first

b) **Confidence-based stopping**:
```python
After each iteration:
    score = LLM evaluation: "Rate 0-10: How well can you answer the query?"
    
    if score >= 8:
        STOP and synthesize
    elif score < 5 and iterations >= 5:
        STOP (probably can't answer)
    else:
        CONTINUE with next most uncertain hypothesis
```

c) **Diminishing returns**:
   - Track information gain per iteration
   - If last 2 iterations added <5 new observations: STOP

d) **Coverage check**:
   - Have we addressed each sub-question?
   - If essential sub-questions remain at 0% confidence after 5 iterations: STOP

**Critical**: The LLM must **explicitly reason** about whether to continue. This is not automatic—it's a prompted decision.

**6. Evidence Synthesis**
- Input: Query, sub-questions, observations, hypotheses
- Output: Answer + evidence chain + uncertainties
- Format: 
  - Direct answer to query
  - "Bottom-line up front" summary
  - Supporting evidence with observation IDs
  - Known uncertainties/contradictions
  - Reasoning trace

### Framework Integration

#### LangGraph for Orchestration

**Why**: LangGraph provides built-in state management, conditional routing, iteration control, and persistence.

**Key Features to Use**:
1. **StateGraph**: Manages agent working memory (observations, hypotheses, iterations)
2. **Conditional Edges**: Implements "should continue?" logic
3. **Checkpointers**: Stores state at each step (for debugging, human-in-the-loop, session memory)
4. **Recursion Limits**: Built-in max iteration enforcement

**Example Structure**:
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

class AgentState(TypedDict):
    query: str
    sub_questions: List[Dict]
    observations: List[Dict]
    hypotheses: List[Dict]
    evidence_trail: List[str]
    iterations: int
    confidence_score: float
    answer: str

workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("decompose", decompose_query)
workflow.add_node("gather", gather_observations)
workflow.add_node("detect_patterns", detect_patterns)
workflow.add_node("test_hypotheses", test_hypotheses)
workflow.add_node("meta_reason", meta_reasoning)
workflow.add_node("synthesize", synthesize_answer)

# Edges
workflow.set_entry_point("decompose")
workflow.add_edge("decompose", "gather")
workflow.add_edge("gather", "detect_patterns")
workflow.add_edge("detect_patterns", "test_hypotheses")
workflow.add_edge("test_hypotheses", "meta_reason")

# Conditional: continue or stop?
workflow.add_conditional_edges(
    "meta_reason",
    should_continue,
    {
        "continue": "gather",
        "synthesize": "synthesize",
        "stop": END
    }
)

workflow.add_edge("synthesize", END)

# Persistence
memory = PostgresSaver.from_conn_string("postgresql://...")
app = workflow.compile(checkpointer=memory, recursion_limit=15)
```

#### DSPy for Optimization (Optional but Recommended)

**Why**: DSPy can automatically optimize prompts and enforce constraints on LLM outputs.

**Key Features to Use**:
1. **Assertions**: Enforce "hypothesis must relate to query" as hard constraint
2. **Suggestions**: Guide "confidence should be based on evidence count"
3. **Optimizers**: Auto-improve the prompts for hypothesis formation, meta-reasoning
4. **Reward Functions**: Score hypothesis quality, relevance to query

**Example Integration**:
```python
import dspy

class HypothesisFormation(dspy.Module):
    def __init__(self):
        self.generator = dspy.ChainOfThought(
            "query, sub_question, observations -> hypothesis, confidence, reasoning"
        )
    
    def forward(self, query, sub_question, observations):
        result = self.generator(
            query=query,
            sub_question=sub_question,
            observations=observations
        )
        
        # Enforce: hypothesis must relate to sub-question
        dspy.Assert(
            relates_to_subquestion(result.hypothesis, sub_question),
            "Hypothesis doesn't address the sub-question"
        )
        
        # Guide: confidence should correlate with evidence
        dspy.Suggest(
            result.confidence <= (len(observations) / 10.0),
            "Confidence seems high given limited evidence"
        )
        
        return result

# Use in LangGraph node
hypothesis_module = HypothesisFormation()

def detect_patterns(state: AgentState) -> AgentState:
    for sq in state['sub_questions']:
        if sq['confidence'] < 0.8:  # Needs work
            hypothesis = hypothesis_module(
                query=state['query'],
                sub_question=sq['text'],
                observations=state['observations']
            )
            state['hypotheses'].append(hypothesis)
    return state
```

**Optimization Phase**:
```python
# After building initial system, optimize prompts
from dspy.teleprompt import MIPROv2

# Define metric
def query_answering_quality(example, pred, trace=None):
    # Score based on correctness, evidence quality, efficiency
    score = 0.0
    if correct_answer(pred.answer, example.gold_answer):
        score += 0.6
    if has_evidence_chain(pred):
        score += 0.2
    if pred.iterations <= 8:  # Efficiency bonus
        score += 0.2
    return score

# Optimize
optimizer = MIPROv2(metric=query_answering_quality, auto='light')
optimized_agent = optimizer.compile(agent, trainset=training_queries)
```

### Hypothesis Management

**The Critical Challenge**: How do hypotheses stay relevant to the query and guide useful exploration?

#### Structure

```python
class Hypothesis:
    claim: str                          # "John = J. Smith"
    confidence: float                   # 0.0 - 1.0
    evidence: List[ObservationID]       # Supporting obs
    contradicting_evidence: List[ObservationID]  # Conflicting obs
    relevant_to_subquestion: int        # Which sub-Q does this help?
    impact_on_answer: str               # "If true: X, if false: Y"
    tested_at_iteration: int            # When was this last evaluated
    num_tests: int                      # How many times tested
```

#### Lifecycle

1. **Formation**: Pattern detection creates hypotheses
2. **Relevance Check**: Must link to a sub-question
3. **Impact Assessment**: LLM explains how this affects the final answer
4. **Testing**: If uncertain and high-impact, gather more evidence
5. **Update**: Confidence changes based on new observations
6. **Resolution**: Accepted (>0.85), Rejected (<0.15), or Uncertain (middle)

#### Storage Options

**Option 1: Session-Only (Simplest)**
- Hypotheses live only in LangGraph's working memory during query
- No cross-query reuse
- Pro: Simple, no stale beliefs
- Con: Wastes computation on repeated queries

**Option 2: Session + Light Cache**
- Working memory during query
- After query: cache high-confidence hypotheses (>0.9) with metadata
- Future queries: load cached beliefs as "priors" but allow challenge
- Pro: Efficiency gains without rigid commitment
- Con: Need cache invalidation strategy

**Option 3: Probabilistic Entity Store**
- Maintain persistent probabilistic entity clusters
- Structure: `{entity_id, observations[], confidence, last_updated, query_history[]}`
- Queries can use or ignore these priors
- Pro: Cross-query learning
- Con: More complex, risk of belief ossification

**Recommendation**: Start with **Option 1**, add **Option 2** once core system works, consider **Option 3** only if proven necessary by usage patterns.

#### Cache Invalidation (if using Option 2/3)

- **Time-based**: Expire after 30 days
- **Corpus-based**: If new documents added, mark related hypotheses "needs_retest"
- **Contradiction-based**: If new query finds conflicting evidence, invalidate
- **Confidence-based**: Only cache hypotheses with confidence >0.9
- **Provenance-based**: Store which corpus version this came from

## Implementation Strategy

### Phase 1: Core Infrastructure (Weeks 1-2)

**Goal**: Get basic observation storage and retrieval working

**Tasks**:
1. Set up PostgreSQL + pgvector
2. Implement observation schema
3. Build ingestion pipeline:
   - Parse documents
   - Extract observations with embeddings
   - Store with metadata
4. Create basic indices (vector, keyword, temporal)
5. Implement 3-5 basic tools:
   - semantic_search(query, k=20)
   - find_cooccurrences(surface_form)
   - temporal_query(surface_form, start_date, end_date)
6. Test: Can we store 10K observations and retrieve relevant ones in <100ms?

**Success Criteria**: 
- Ingest sample corpus (10K documents)
- Retrieve relevant observations for test queries
- Tools work and return sensible results

### Phase 2: Basic Agent Loop (Weeks 3-4)

**Goal**: Get a simple agent working end-to-end on easy queries

**Tasks**:
1. Set up LangGraph with basic state management
2. Implement simplified workflow:
   - decompose_query
   - gather_observations (1 iteration only)
   - synthesize_answer
3. No hypothesis formation yet—just gather and summarize
4. Test on single-hop queries that can be answered with one retrieval
5. Add hard iteration limit (max 5 for testing)

**Success Criteria**:
- Agent can answer "What did John say about X?" from corpus
- Evidence is cited with observation IDs
- System doesn't crash or loop forever

### Phase 3: Multi-Step Reasoning (Weeks 5-6)

**Goal**: Enable iterative exploration and hypothesis formation

**Tasks**:
1. Add pattern_detection node
2. Add hypothesis formation logic
3. Implement hypothesis testing loop
4. Add confidence tracking
5. Implement basic "should_continue?" logic:
   - Confidence threshold (>0.8 → stop)
   - Max iterations (10)
   - Coverage check (all sub-questions addressed?)
6. Test on 2-3 hop queries requiring multiple observations

**Success Criteria**:
- Agent can answer "Who approved transactions related to Company X?"
- Hypotheses form and strengthen/weaken based on evidence
- System stops when confident or out of budget

### Phase 4: Robustness & Optimization (Weeks 7-8)

**Goal**: Handle edge cases, improve quality, add DSPy optimization

**Tasks**:
1. Add contradiction detection
2. Improve meta-reasoning prompts
3. Add DSPy assertions for hypothesis relevance
4. Build evaluation dataset (50-100 queries with gold answers)
5. Optimize prompts using DSPy
6. Add session persistence (checkpointers)
7. Implement basic caching for high-confidence hypotheses

**Success Criteria**:
- System handles contradictory evidence gracefully
- Prompts are optimized for corpus domain
- Performance improves 20%+ on eval dataset
- Sessions can be resumed

### Phase 5: Scale & Production (Weeks 9-10)

**Goal**: Make it work on real corpus at scale

**Tasks**:
1. Optimize database queries
2. Add pagination for large result sets
3. Implement parallel tool execution where possible
4. Add monitoring/logging
5. Build UI for exploring evidence chains
6. Stress test with 100K+ document corpus
7. Add human-in-the-loop approval gates (LangGraph feature)

**Success Criteria**:
- Works on full-scale corpus
- Query latency <60s for complex queries
- Evidence chains are inspectable
- System is monitorable

## Key Design Decisions

### 1. When to Cluster Observations into Entities?

**Answer**: Only at query time, in working memory, for the specific question being answered.

**Rationale**:
- Different queries need different entity boundaries
- Pre-computing forces premature commitment
- Keeping observations separate preserves maximum flexibility
- Clustering is cheap with good embeddings/indices

### 2. How to Handle Contradictions?

**Answer**: Preserve them explicitly. Don't resolve.

**Rationale**:
- Contradictions are often important signals (fraud, change over time, misinformation)
- Forcing resolution loses information
- The user should see conflicting evidence and judge

**Implementation**: When synthesizing answer, if contradictory observations exist, present both:
```
"Sources disagree on Project X:
- Doc A (March 15): Project cancelled (obs_42)
- Doc B (April 20): Project delivered on time (obs_91)

Possible explanations:
1. Plans changed between March and April
2. Different projects with same name
3. One source is incorrect"
```

### 3. How Much to Pre-compute?

**Answer**: Pre-compute indices, not conclusions.

**Pre-compute**:
- Vector embeddings
- Co-occurrence statistics
- Temporal orderings
- Basic metadata extraction

**Don't pre-compute**:
- Entity resolutions
- Relationship inferences
- Contradiction resolutions
- Answer-specific patterns

### 4. How to Prevent Irrelevant Exploration?

**Answer**: Explicit relevance tracking + DSPy assertions.

**Mechanism**:
1. Every hypothesis links to a sub-question
2. Every sub-question explains why it's needed for the answer
3. DSPy assertions enforce: `relates_to_query(hypothesis) == True`
4. Meta-reasoning step filters low-impact hypotheses

**Prompt Pattern**:
```
You've formed hypothesis: "John likes coffee"

Does this help answer the original query: "Who approved transaction T?"
- Sub-Q1 (What is T?): No
- Sub-Q2 (Who are approvers?): No
- Sub-Q3 (Who approved T?): No

→ REJECT: Irrelevant hypothesis. Don't pursue.
```

### 5. LLM vs Heuristics for Pattern Detection?

**Answer**: LLM-first, heuristics for validation.

**Rationale**:
- LLMs are excellent at noticing patterns in text
- Heuristics are brittle and domain-specific
- But heuristics can validate LLM outputs (e.g., "these embeddings are similar")

**Hybrid Approach**:
```python
# LLM suggests: "John = J. Smith"
hypothesis = llm_pattern_detection(observations)

# Heuristic validates
if embedding_similarity(obs_john, obs_jsmith) < 0.6:
    hypothesis.confidence *= 0.5  # Downweight

if cooccurrence_count(obs_john, obs_jsmith) > 5:
    hypothesis.confidence *= 1.2  # Upweight
```

## Evaluation

### Dimensions

1. **Answer Correctness**
   - Binary: Did it get the right answer?
   - Metric: Accuracy on held-out questions with gold labels

2. **Evidence Quality**
   - Are cited observations actually relevant?
   - Are all claims backed by evidence?
   - Metric: Human evaluation of evidence chains

3. **Efficiency**
   - How many iterations did it take?
   - How many tokens consumed?
   - Metric: Average iterations, token count per query

4. **Handling Uncertainty**
   - Does it correctly identify when it can't answer?
   - Are confidence scores calibrated?
   - Metric: Calibration curve, precision of "I don't know"

5. **Multi-Hop Performance**
   - Can it connect evidence across multiple hops?
   - Does it find implicit patterns?
   - Metric: Accuracy on 2-hop, 3-hop, 4-hop questions

6. **Contradiction Detection**
   - Does it notice conflicting evidence?
   - Does it present both sides?
   - Metric: Precision/recall on known contradictions

### Benchmark Datasets

**Start with existing**:
- HotpotQA (multi-hop question answering)
- MuSiQue (connected multi-hop questions)
- MEQA (event-centric multi-hop)

**Adapt for ECU**:
- Add questions requiring implicit inference
- Add questions with contradictory sources
- Add questions requiring entity resolution

**Build domain-specific**:
- Use your actual corpus
- Create 50-100 gold-labeled queries
- Include easy (1-hop), medium (2-3 hop), hard (4+ hop, implicit)

### Success Metrics

**MVP (Phase 1-3)**:
- 60% accuracy on 1-hop questions
- 40% accuracy on 2-hop questions
- Evidence chains present for 90% of answers
- Average query time <30 seconds

**Production (Phase 5)**:
- 80% accuracy on 1-hop questions
- 60% accuracy on 2-3 hop questions
- 40% accuracy on 4+ hop or implicit questions
- Evidence quality rated >4/5 by domain experts
- 90%+ of irrelevant hypotheses filtered out
- Average query time <60 seconds

## Edge Cases & Challenges

### Challenge 1: Infinite Loops

**Problem**: Agent keeps revisiting same hypotheses without learning.

**Solutions**:
- Track which observation clusters have been explored
- DSPy assertion: "Don't repeat past queries within same session"
- Diminishing returns check: "Last 2 iterations added no new info"

### Challenge 2: Premature Convergence

**Problem**: Agent stops too early with low-quality answer.

**Solutions**:
- Minimum iteration requirement for complex queries (≥5)
- Confidence calibration: Don't trust first answer
- Multiple hypothesis tracking: Maintain 2-3 competing explanations

### Challenge 3: Explosion of Hypotheses

**Problem**: Agent forms hundreds of hypotheses, can't focus.

**Solutions**:
- Max hypotheses per sub-question (e.g., 5)
- Prune low-confidence hypotheses after each iteration
- Focus on high-impact hypotheses (big effect on final answer)

### Challenge 4: Context Window Overflow

**Problem**: Working memory grows too large for LLM context.

**Solutions**:
- Summarize observations after each iteration (keep full versions in DB)
- Hierarchical memory: Keep only recent iterations in full detail
- Use LangGraph checkpointers to page state in/out

### Challenge 5: Stale Cached Hypotheses

**Problem**: System reuses old beliefs that are now wrong.

**Solutions**:
- Conservative caching: Only cache very high confidence (>0.95)
- Short TTL: 7-30 days depending on corpus update frequency
- Conflict detection: If new evidence contradicts cache, invalidate
- Provenance tracking: Store corpus version with each cached hypothesis

## Non-Goals

**What This System Is NOT**:

1. **Not a traditional search engine**: Doesn't just return relevant documents
2. **Not a Q&A system for simple facts**: Use standard RAG for "What is X?"
3. **Not real-time**: Designed for analytical queries (30-60 sec acceptable)
4. **Not a knowledge graph builder**: Doesn't create persistent, fixed entity structures
5. **Not a fact-checking system**: Doesn't determine absolute truth, presents evidence

## References & Further Reading

### Core Concepts
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
  - Key insight: "Agents = workflows + loops" - don't over-complicate
  - Emphasis on deterministic workflows where possible

### Frameworks
- [LangGraph Documentation](https://langchain.com/langgraph)
  - State management, conditional routing, persistence
- [DSPy Documentation](https://dspy.ai)
  - Assertions, optimizers, prompt engineering automation

### Academic Background
- HotpotQA: Multi-hop question answering dataset and baselines
- MuSiQue: Connected multi-hop questions requiring genuine reasoning
- DSPy Assertions paper: Computational constraints for self-refining LM pipelines

### Vector Databases
- pgvector vs specialized vector DBs benchmarks
- When to use PostgreSQL vs Neo4j for graph traversal

## Getting Started

### Prerequisites

**Technical Skills**:
- Python proficiency
- SQL/database experience
- LLM prompting experience
- Understanding of embeddings/vector search

**Infrastructure**:
- PostgreSQL instance (or cloud equivalent)
- LLM API access (Claude, GPT-4, or open-source models)
- Compute for embedding generation

### First Steps

1. **Set up minimal observation store**:
   - PostgreSQL + pgvector
   - Basic observation schema
   - Ingest 1000 test documents

2. **Build single-iteration agent**:
   - LangGraph workflow
   - One semantic search tool
   - Simple synthesize node
   - Test on trivial queries

3. **Iterate from there**:
   - Add complexity incrementally
   - Test at each stage
   - Don't build all tools before proving core loop works

### Development Workflow

```
1. Start simple: Answer 1-hop questions with single retrieval
2. Add complexity: Multi-step reasoning for 2-hop questions
3. Add robustness: Handle contradictions, uncertainty
4. Optimize: Use DSPy to improve prompts
5. Scale: Bigger corpus, more complex queries
```

### Success Indicators (Early Stage)

**Week 1**: Can store and retrieve observations
**Week 2**: Agent can answer "What did X say about Y?" 
**Week 3**: Agent can answer "X said A, Y said B, what's the relationship?"
**Week 4**: Agent can answer multi-hop queries requiring 2-3 steps

If you're hitting these milestones, you're on track.

## Appendix: Example Queries

### Simple (1-hop, should work in Phase 2)
- "What did John say about the merger?"
- "When was Project X mentioned?"
- "Who attended the March 15 meeting?"

### Medium (2-3 hop, should work in Phase 3)
- "Who approved transactions for companies mentioned in the leaked emails?"
- "What features were added between v2.0 and v3.0?"
- "Which investigators worked on cases involving Company X?"

### Hard (4+ hop or implicit, should work in Phase 4+)
- "Are there patterns in how Project Y was described before and after the funding announcement?"
- "What network of relationships connects Person A to Organization B?"
- "Which claims in Document X are contradicted by later documents?"

### Very Hard (Emergent understanding, stretch goal)
- "What narrative emerges about Company X's financial practices from scattered mentions across emails, transactions, and news articles?"
- "How did the codebase's architecture evolve and what were the key decision points?"
- "What implicit pattern suggests these seemingly unrelated events are actually coordinated?"

---

## Final Notes

This is an ambitious project that pushes beyond current RAG/agent capabilities. The key innovations are:

1. **Observation-first architecture**: No premature entity commitment
2. **Query-time pattern formation**: Understanding emerges through reasoning
3. **Explicit uncertainty**: Contradictions and confidence are first-class
4. **Evidence-grounded**: Every claim traces to observations

Start simple, iterate fast, and prove each capability before adding the next. The frameworks (LangGraph, DSPy) handle many of the hard parts—focus on the novel aspects: observation store design, hypothesis management, and meta-reasoning about when to explore vs exploit.

Good luck building!
