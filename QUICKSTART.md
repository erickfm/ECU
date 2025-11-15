# ECU System - Quick Start Guide

Get the Emergent Corpus Understanding system running in 5 minutes!

## Prerequisites Check

```bash
# Check Python
python3 --version  # Should be 3.9+

# Check PostgreSQL
psql --version     # Should be 14+

# Check OpenAI key
echo $OPENAI_API_KEY  # Or add to .env
```

## 1. Setup (2 minutes)

```bash
# Navigate to project
cd /Users/erick/ECU

# Install dependencies
pip install -r requirements.txt

# Verify .env file exists with your OpenAI key
cat .env
```

## 2. Initialize Database (1 minute)

```bash
# Create database
createdb ecu_db

# Setup schema
python scripts/setup_database.py
```

**Expected output:**
```
✓ Database setup complete!
```

## 3. Ingest Sample Data (2 minutes)

```bash
# Ingest first 100 documents for testing
python scripts/ingest_documents.py --limit 100
```

**Expected output:**
```
Processing batches: 100%
✓ Completed processing 100 files
```

## 4. Try It Out!

### Option A: Interactive CLI

```bash
python main.py interactive
```

Try these queries:
- `Who is Jeffrey Epstein?`
- `What organizations are mentioned?`
- `What did the oversight committee investigate?`

### Option B: Web Interface

**Terminal 1:**
```bash
python scripts/run_server.py
```

**Terminal 2:**
```bash
cd web && python -m http.server 3000
```

Open: http://localhost:3000

### Option C: Single Query

```bash
python main.py query "Who is Jeffrey Epstein?"
```

## What You've Built

✅ **Observation Store**: PostgreSQL + pgvector with 100+ documents  
✅ **Retrieval Tools**: Semantic search, co-occurrence, temporal queries  
✅ **Agent Loop**: LangGraph-based multi-step reasoning  
✅ **Hypothesis Formation**: Dynamic pattern detection  
✅ **Evidence Chains**: Traceable reasoning paths  
✅ **API Server**: REST API for programmatic access  
✅ **Web UI**: Beautiful interface for queries  

## Next Steps

### Ingest Full Corpus

```bash
# This will take 30-60 minutes
python scripts/ingest_documents.py
```

### Run Demo Queries

```bash
python scripts/demo_queries.py
```

### Explore the API

```bash
# Open API docs
open http://localhost:8000/docs
```

### Optimize Performance

Edit `.env`:
```bash
MAX_ITERATIONS=10          # Faster responses
SEMANTIC_SEARCH_K=30       # Better recall
CHUNK_SIZE=300             # Smaller chunks
```

## Example Queries by Complexity

### Simple (1-2 iterations)
- "What is the date of the first document?"
- "Who is mentioned most frequently?"
- "What locations are referenced?"

### Medium (3-5 iterations)
- "What organizations are connected to Epstein?"
- "What investigation methods did the committee use?"
- "When did key events occur?"

### Complex (5-10 iterations)
- "What patterns exist in how the investigation evolved?"
- "Are there contradictions in witness statements?"
- "What implicit connections exist between entities?"

## Architecture Overview

```
Your Query
    ↓
┌─────────────────────┐
│   LangGraph Agent   │
│  1. Decompose       │
│  2. Gather Evidence │
│  3. Form Hypotheses │
│  4. Test & Iterate  │
│  5. Synthesize      │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Retrieval Tools    │
│  • Semantic Search  │
│  • Co-occurrence    │
│  • Temporal Query   │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Observation Store   │
│ PostgreSQL+pgvector │
└─────────────────────┘
```

## Troubleshooting

### "Database does not exist"
```bash
createdb ecu_db
python scripts/setup_database.py
```

### "No observations found"
```bash
python scripts/ingest_documents.py --limit 100
```

### "Connection refused"
```bash
# Start PostgreSQL
brew services start postgresql@14  # macOS
sudo systemctl start postgresql    # Linux
```

### "OpenAI API error"
```bash
# Check your .env file
cat .env | grep OPENAI_API_KEY
```

### "Server won't start"
```bash
# Check port 8000 is free
lsof -i :8000
# Use different port
python scripts/run_server.py --port 8080
```

## Performance Expectations

- **Ingestion**: ~1000 docs/minute
- **Simple queries**: 5-15 seconds
- **Complex queries**: 20-60 seconds
- **Storage**: ~500KB per 1000 observations

## Full Documentation

- **Complete Guide**: `DEPLOYMENT.md`
- **System Spec**: `emergent-corpus-understanding-spec.md`
- **Code Documentation**: `README.md`

## Success Indicators

After quickstart, you should have:

✅ Database with 100+ observations  
✅ Working CLI that answers questions  
✅ API server running on port 8000  
✅ Web UI accessible on port 3000  
✅ Evidence chains showing reasoning  
✅ Confidence scores 6-9/10 on simple queries  

## Common First Queries

1. **"Who is Jeffrey Epstein?"**  
   Expected: High confidence (8+), 2-3 iterations, biographical info

2. **"What organizations are mentioned?"**  
   Expected: Medium confidence (7+), 3-5 iterations, list of entities

3. **"What contradictions exist?"**  
   Expected: Lower confidence (6+), 5-8 iterations, conflicting statements

## Help & Support

- **Logs**: `logs/ecu_*.log`
- **Database Stats**: `psql ecu_db -c "SELECT COUNT(*) FROM observations;"`
- **API Health**: `curl http://localhost:8000/`

Happy exploring! 🧠

