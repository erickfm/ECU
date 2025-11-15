# 🧠 ECU System - START HERE

Welcome to the **Emergent Corpus Understanding (ECU)** system!

---

## ⚡ Quick Start (5 minutes)

```bash
cd /Users/erick/ECU

# 1. Setup
./scripts/quickstart.sh

# 2. Verify
python scripts/verify_installation.py

# 3. Try it!
python main.py interactive
```

**Try these queries:**
- "Who is Jeffrey Epstein?"
- "What organizations are mentioned in the documents?"
- "What did the oversight committee investigate?"

---

## 📚 Documentation Guide

### For First-Time Users
1. **START_HERE.md** ← You are here
2. **QUICKSTART.md** - 5-minute setup
3. **README.md** - Full system overview

### For Developers
1. **PROJECT_SUMMARY.md** - Technical architecture
2. **emergent-corpus-understanding-spec.md** - Original specification
3. **COMMANDS.md** - Command reference

### For Production
1. **DEPLOYMENT.md** - Production deployment guide
2. **IMPLEMENTATION_COMPLETE.md** - Completion status

---

## 🎯 What You Have

### ✅ Complete System (All 5 Phases Done!)

**Phase 1**: Core Infrastructure
- PostgreSQL + pgvector database
- Observation store with embeddings
- Document ingestion pipeline

**Phase 2**: Basic Agent
- LangGraph workflow
- Query decomposition
- Answer synthesis

**Phase 3**: Multi-Step Reasoning
- Hypothesis formation & testing
- Confidence tracking
- Iteration control

**Phase 4**: Robustness
- Contradiction detection
- DSPy optimization
- Error handling

**Phase 5**: Production
- REST API server
- Web interface
- Monitoring & stats

### 📊 Dataset
- **23,000 OCR documents** from House Oversight Committee
- Perfect for investigative journalism use case
- Real-world data, not toy examples

---

## 🚀 Three Ways to Use ECU

### 1. Interactive CLI (Recommended for first time)
```bash
python main.py interactive
```

### 2. Web Interface (Best UX)
```bash
# Terminal 1: API
python scripts/run_server.py

# Terminal 2: Web UI  
cd web && python -m http.server 3000

# Open: http://localhost:3000
```

### 3. Programmatic (For integration)
```python
from sqlalchemy import create_engine
from src.agent import ECUAgent
from src.config import config

engine = create_engine(config.DATABASE_URL)
agent = ECUAgent(engine)

result = agent.query("Your question here")
print(result['answer'])
```

---

## 💡 How It Works

```
Your Question
     ↓
┌─────────────────────┐
│   1. Decompose      │  Break into sub-questions
│   2. Gather         │  Retrieve relevant observations
│   3. Detect         │  Find patterns & hypotheses
│   4. Test           │  Validate with evidence
│   5. Reason         │  Should we continue?
│   6. Synthesize     │  Create final answer
└─────────────────────┘
     ↓
Answer + Evidence Chain + Confidence
```

**Key Innovation**: Understanding emerges during the query, not before!

---

## 📖 Example Session

```bash
$ python main.py interactive

Query> Who is Jeffrey Epstein?

[System processes query...]

ANSWER:
Jeffrey Epstein was an American financier and convicted sex 
offender who became the subject of House Oversight Committee 
investigation. Documents show he had connections to various 
high-profile individuals and organizations...

CONFIDENCE: 8.5/10
ITERATIONS: 3
OBSERVATIONS: 45

EVIDENCE TRAIL:
  Decomposed query into 3 sub-questions
  Tool semantic_search: "Epstein biography" -> 20 observations
  Formed hypothesis: "Epstein = financier" (confidence: 0.8)
  Tool semantic_search: "Epstein conviction" -> 15 observations
  Updated hypothesis: confidence 0.8 -> 0.9
  Meta-reasoning: confidence=8.5, decision=SYNTHESIZE
  Synthesized final answer
```

---

## 🎨 What Makes ECU Special

### 1. **Observation-First**
No premature entity resolution. "John" and "J. Smith" stay separate until a query needs to connect them.

### 2. **Query-Time Reasoning**
Patterns emerge during inquiry, not at indexing time. Like a human expert reading through documents.

### 3. **Evidence Grounding**
Every claim traces to specific documents. Full auditability for compliance and investigations.

### 4. **Contradiction Detection**
Conflicting information is presented, not hidden. See both sides of disputed facts.

### 5. **Multi-Hop Reasoning**
Connect information across 4+ documents to answer complex questions.

---

## 🛠️ Common Tasks

### Ingest More Data
```bash
# Ingest full corpus (30-60 min)
python scripts/ingest_documents.py

# Or in chunks
python scripts/ingest_documents.py --limit 5000
```

### Run Demo Queries
```bash
python scripts/demo_queries.py
```

### Start API Server
```bash
python scripts/run_server.py
# API Docs: http://localhost:8000/docs
```

### View Statistics
```bash
curl http://localhost:8000/stats
```

### Check Logs
```bash
tail -f logs/ecu_*.log
```

---

## 🆘 Troubleshooting

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
# Check PostgreSQL is running
pg_isready

# Start if needed (macOS)
brew services start postgresql@14
```

### Need Help?
1. Run: `python scripts/verify_installation.py`
2. Check: `logs/ecu_*.log`
3. See: `DEPLOYMENT.md` for detailed troubleshooting

---

## 📊 System Status

```
✅ Database: PostgreSQL + pgvector
✅ Storage: Observation store
✅ Ingestion: Document processor
✅ Retrieval: 6 tools
✅ Agent: LangGraph workflow  
✅ API: FastAPI server
✅ UI: Web interface
✅ Tests: Basic test suite
✅ Docs: Comprehensive guides
```

**Status**: Production Ready! 🚀

---

## 🎯 Next Steps

### First Time Users
1. ✅ You're here!
2. Run `./scripts/quickstart.sh`
3. Try `python main.py interactive`
4. Read `README.md` for details

### Developers
1. Read `PROJECT_SUMMARY.md`
2. Review `src/agent/workflow.py`
3. Check `COMMANDS.md` for reference
4. Run `pytest tests/`

### Production Users
1. Read `DEPLOYMENT.md`
2. Configure `.env` properly
3. Set up monitoring
4. Deploy with Docker

---

## 📞 Support

- **Logs**: `logs/ecu_*.log`
- **Verification**: `python scripts/verify_installation.py`
- **API Docs**: http://localhost:8000/docs (when server running)
- **Database**: `psql ecu_db`

---

## 🎉 You're Ready!

The ECU system is:
- ✅ Fully implemented (all 5 phases)
- ✅ Tested with real data
- ✅ Production ready
- ✅ Documented comprehensively

**Let's explore emergent understanding! 🧠**

---

**Quick Commands:**
```bash
Setup:     ./scripts/quickstart.sh
Verify:    python scripts/verify_installation.py
Query:     python main.py interactive
API:       python scripts/run_server.py
Web UI:    cd web && python -m http.server 3000
Demo:      python scripts/demo_queries.py
Ingest:    python scripts/ingest_documents.py --limit 100
Stats:     curl http://localhost:8000/stats
Logs:      tail -f logs/ecu_*.log
Help:      Read README.md
```

Happy exploring! 🚀

