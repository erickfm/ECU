# Emergent Corpus Understanding (ECU) System

A system that develops **emergent understanding** of large, messy corpora through query-time reasoning, comparable to a domain expert who has lived with material for years.

## Overview

The ECU system addresses a fundamental gap in current document understanding systems: most treat documents as independent retrieval sources, but many important insights are **distributed**, **emergent**, **implicit**, **inductive**, and **provable** only through evidence chains across hundreds or thousands of sources.

### Key Features

- **Observation-First Architecture**: No premature entity commitment - keeps observations separate and flexible
- **Query-Time Reasoning**: Understanding emerges during the act of inquiry, not at indexing time
- **Multi-Hop Evidence Chains**: Connects information across multiple documents and reasoning steps
- **Hypothesis Formation & Testing**: Dynamically forms and tests hypotheses about entities and relationships
- **Contradiction Detection**: Preserves conflicting evidence rather than resolving it away
- **Evidence Grounding**: Every conclusion traces back to specific observations

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Agent Reasoning Loop (LangGraph)               │
│  1. Query Decomposition                                     │
│  2. Observation Gathering (tool calls)                      │
│  3. Pattern Detection                                       │
│  4. Hypothesis Formation & Testing                          │
│  5. Meta-Reasoning & Iteration Control                      │
│  6. Evidence Synthesis                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 Tool Layer (Retrieval)                       │
│  • semantic_search()      • find_cooccurrences()            │
│  • temporal_query()       • traverse_graph()                │
│  • cluster_observations() • find_contradictions()           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Observation Store                         │
│         PostgreSQL + pgvector + Co-occurrence Graph         │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 14+ with pgvector extension
- OpenAI API key (or use local embeddings)

### Setup

1. **Clone and install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**

Create a `.env` file:

```bash
OPENAI_API_KEY=your-key-here
DATABASE_URL=postgresql://localhost:5432/ecu_db
```

3. **Initialize the database:**

```bash
# Create PostgreSQL database
createdb ecu_db

# Setup schema and extensions
python scripts/setup_database.py
```

4. **Ingest your corpus:**

```bash
# Ingest first 1000 documents (for testing)
python scripts/ingest_documents.py --limit 1000

# Ingest all documents
python scripts/ingest_documents.py
```

## Usage

### Interactive Mode

```bash
python main.py interactive
```

Example queries:
- "What did Jeffrey Epstein say about Project X?"
- "Who approved transactions related to the foundation?"
- "Are there contradictions in how the investigation was described?"

### Single Query Mode

```bash
python main.py query "Who are the key people mentioned in the documents?"
```

### Programmatic Usage

```python
from sqlalchemy import create_engine
from src.agent import ECUAgent
from src.config import config

# Create agent
engine = create_engine(config.DATABASE_URL)
agent = ECUAgent(engine)

# Run query
result = agent.query("What patterns exist in the oversight documents?")

print(result['answer'])
print(f"Confidence: {result['confidence']}/10")
print(f"Evidence: {len(result['observations_count'])} observations")
```

## System Components

### 1. Observation Store (`src/database/`)

- **PostgreSQL + pgvector**: Stores observations (document chunks) with embeddings
- **Co-occurrence Graph**: Tracks relationships between observations
- **No Entity Resolution**: Keeps "John", "J. Smith", etc. separate until query time

### 2. Ingestion Pipeline (`src/ingestion/`)

- **Document Processor**: Chunks documents, generates embeddings
- **Observation Creation**: Each chunk becomes an independent observation
- **Co-occurrence Tracking**: Links adjacent and related observations

### 3. Tool Layer (`src/tools/`)

Tools for retrieving observations:

- `semantic_search(query, k)`: Vector similarity search
- `find_cooccurrences(surface_form)`: Find related observations
- `temporal_query(keyword, date_range)`: Time-based queries
- `traverse_graph(obs_id, hops)`: Follow co-occurrence links
- `cluster_observations(obs_ids)`: Group similar observations
- `find_contradictions(query)`: Identify conflicting evidence

### 4. Agent Layer (`src/agent/`)

**LangGraph-based reasoning loop:**

1. **Query Decomposition**: Break complex queries into sub-questions
2. **Observation Gathering**: Use tools to collect relevant evidence
3. **Pattern Detection**: Identify relationships, coreferences, patterns
4. **Hypothesis Testing**: Form and test hypotheses about entities/relationships
5. **Meta-Reasoning**: Decide whether to continue or synthesize answer
6. **Synthesis**: Create final answer with evidence chains

## Configuration

Edit `.env` or `src/config.py`:

```python
# Agent behavior
MAX_ITERATIONS = 15              # Maximum reasoning iterations
CONFIDENCE_THRESHOLD = 0.8       # Stop when confidence reaches this
MIN_CONFIDENCE_CONTINUE = 0.5    # Stop if confidence stays below this

# Retrieval
SEMANTIC_SEARCH_K = 20           # Results per semantic search
CHUNK_SIZE = 500                 # Words per observation chunk
CHUNK_OVERLAP = 50               # Overlap between chunks

# LLM
OPENAI_MODEL = "gpt-4-turbo-preview"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
```

## Example Queries

### Simple (1-hop)
- "What did John say about the merger?"
- "When was Project X mentioned?"

### Medium (2-3 hop)
- "Who approved transactions for companies mentioned in the emails?"
- "What investigators worked on cases involving Organization X?"

### Hard (4+ hop, implicit)
- "Are there patterns in how Project Y was described before and after the funding announcement?"
- "What network of relationships connects Person A to Organization B?"

### Very Hard (Emergent understanding)
- "What narrative emerges about the investigation from scattered mentions across documents?"
- "What implicit patterns suggest these events are coordinated?"

## Development

### Project Structure

```
ECU/
├── src/
│   ├── agent/          # LangGraph agent implementation
│   ├── database/       # Schema and database utilities
│   ├── ingestion/      # Document processing pipeline
│   ├── tools/          # Retrieval tools
│   └── utils/          # Embeddings, helpers
├── scripts/            # Setup and ingestion scripts
├── tests/             # Test suite
├── data/              # Cache and checkpoints
├── logs/              # Application logs
└── main.py            # CLI entry point
```

### Running Tests

```bash
pytest tests/
```

### Adding New Tools

1. Add method to `src/tools/retrieval_tools.py`
2. Update `GATHER_OBSERVATIONS_PROMPT` in `src/agent/prompts.py`
3. Add tool execution logic in `gather_observations()` in `src/agent/workflow.py`

## Performance

- **Ingestion**: ~1000 documents/minute (with local embeddings)
- **Query**: 10-60 seconds for complex queries (depends on iterations)
- **Storage**: ~500KB per 1000 observations (with embeddings)

## Limitations & Future Work

### Current Limitations
- Single-threaded tool execution (could parallelize)
- No caching of high-confidence hypotheses (planned)
- Limited to text documents (no images, structured data yet)
- English language only (embeddings are multilingual though)

### Planned Enhancements
- **Phase 4**: DSPy optimization, contradiction detection
- **Phase 5**: Parallel tool execution, monitoring, UI
- **Future**: Multi-modal support, streaming results, human-in-the-loop

## Architecture Decisions

### Why Observation-First?

Traditional systems force entity resolution at indexing time, but different queries need different entity boundaries. "John" and "J. Smith" might be the same person for one query but different for another. The observation-first approach preserves maximum flexibility.

### Why Query-Time Reasoning?

Like a human expert, the system doesn't understand the corpus until it tries to answer a question. The reasoning process IS the pattern discovery process.

### Why LangGraph?

LangGraph provides:
- Built-in state management
- Conditional routing
- Iteration control
- Session persistence (checkpoints)
- Human-in-the-loop capabilities

### Why PostgreSQL + pgvector?

- Single system (simpler than separate vector + relational DBs)
- Good performance up to 100M observations
- Mature, well-understood
- Supports both structured queries and vector search

## References

- [Full System Specification](emergent-corpus-understanding-spec.md)
- [LangGraph Documentation](https://langchain.com/langgraph)
- [pgvector](https://github.com/pgvector/pgvector)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)

## License

MIT

## Contributing

Contributions welcome! Please see the specification for system design principles and architecture decisions.
