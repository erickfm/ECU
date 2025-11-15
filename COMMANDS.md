# ECU System - Command Reference

Quick reference for all ECU system commands.

---

## 🚀 Setup Commands

### Initial Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create database
createdb ecu_db

# Initialize schema
python scripts/setup_database.py

# Quick setup (all in one)
./scripts/quickstart.sh
```

### Verify Installation
```bash
# Run all checks
python scripts/verify_installation.py

# Check database
psql ecu_db -c "\dt"

# Check observations
psql ecu_db -c "SELECT COUNT(*) FROM observations;"
```

---

## 📥 Ingestion Commands

### Basic Ingestion
```bash
# Ingest first 100 files (for testing)
python scripts/ingest_documents.py --limit 100

# Ingest first 1000 files
python scripts/ingest_documents.py --limit 1000

# Ingest all files
python scripts/ingest_documents.py

# Ingest from custom directory
python scripts/ingest_documents.py --directory /path/to/docs --limit 500
```

### Monitor Ingestion
```bash
# Watch log in real-time
tail -f logs/ecu_*.log

# Count observations
watch -n 5 'psql ecu_db -c "SELECT COUNT(*) FROM observations;"'
```

---

## 🔍 Query Commands

### Interactive Mode
```bash
# Start interactive CLI
python main.py interactive

# Within interactive mode:
Query> Who is Jeffrey Epstein?
Query> What organizations are mentioned?
Query> quit  # to exit
```

### Single Query
```bash
# Run single query
python main.py query "Who is Jeffrey Epstein?"

# Save results to file
python main.py query "Your question?" --output results.json
```

### Demo Queries
```bash
# Run demonstration with example queries
python scripts/demo_queries.py
```

---

## 🌐 API Server Commands

### Start Server
```bash
# Start on default port (8000)
python scripts/run_server.py

# Start on custom port
python scripts/run_server.py --port 8080

# Start with auto-reload (development)
python scripts/run_server.py --reload

# Start on all interfaces
python scripts/run_server.py --host 0.0.0.0
```

### Test API
```bash
# Health check
curl http://localhost:8000/

# Run query via API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Who is Jeffrey Epstein?"}'

# Get statistics
curl http://localhost:8000/stats

# List recent sessions
curl http://localhost:8000/sessions

# View API docs
open http://localhost:8000/docs
```

---

## 🖥️ Web UI Commands

### Start Web UI
```bash
# Terminal 1: Start API
python scripts/run_server.py

# Terminal 2: Start web server
cd web
python -m http.server 3000

# Open in browser
open http://localhost:3000
```

---

## 🗄️ Database Commands

### Query Database
```bash
# Connect to database
psql ecu_db

# Count observations
psql ecu_db -c "SELECT COUNT(*) FROM observations;"

# Count by document
psql ecu_db -c "
  SELECT LEFT(doc_id, 30) as doc,
         COUNT(*) as count
  FROM observations
  GROUP BY doc
  ORDER BY count DESC
  LIMIT 10;
"

# Check recent sessions
psql ecu_db -c "
  SELECT session_id, 
         query,
         iterations,
         confidence_score
  FROM query_sessions
  ORDER BY created_at DESC
  LIMIT 5;
"
```

### Database Maintenance
```bash
# Backup database
pg_dump ecu_db > backup.sql
gzip backup.sql

# Restore database
gunzip -c backup.sql.gz | psql ecu_db_new

# Vacuum and analyze
psql ecu_db -c "VACUUM ANALYZE;"

# Rebuild indices
psql ecu_db -c "REINDEX DATABASE ecu_db;"
```

---

## 🧪 Testing Commands

### Run Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src

# Run specific test
pytest tests/test_basic.py

# Verbose output
pytest tests/ -v
```

### Manual Testing
```bash
# Test ingestion (small dataset)
python scripts/ingest_documents.py --limit 10

# Test query
python main.py query "test query"

# Test API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

---

## 📊 Monitoring Commands

### View Logs
```bash
# Tail logs
tail -f logs/ecu_*.log

# Search for errors
grep ERROR logs/ecu_*.log

# Search for specific session
grep "session_123" logs/ecu_*.log

# Last 100 lines
tail -n 100 logs/ecu_*.log
```

### System Stats
```bash
# Database size
psql ecu_db -c "
  SELECT pg_size_pretty(pg_database_size('ecu_db'));
"

# Table sizes
psql ecu_db -c "
  SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::text)) as size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(tablename::text) DESC;
"

# API stats
curl http://localhost:8000/stats | jq .
```

---

## 🔧 Maintenance Commands

### Clean Up
```bash
# Remove logs
rm logs/*.log

# Clear cache
rm -rf data/cache/*

# Remove checkpoints
rm data/checkpoints.db

# Clean Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
```

### Reset Database
```bash
# Drop and recreate
dropdb ecu_db
createdb ecu_db
python scripts/setup_database.py
```

### Update Dependencies
```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade openai

# Freeze current versions
pip freeze > requirements.txt
```

---

## 🐳 Docker Commands

### Build and Run
```bash
# Build image
docker build -t ecu-system .

# Run container
docker run -d -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  ecu-system

# Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 🔑 Environment Commands

### View Configuration
```bash
# Show current config
cat .env

# Check specific variable
echo $OPENAI_API_KEY

# Load environment
source .env
export $(cat .env | xargs)
```

### Update Configuration
```bash
# Edit config
nano .env

# Add variable
echo "NEW_VAR=value" >> .env

# Reload
source .env
```

---

## 📈 Performance Commands

### Profile Query
```bash
# Time a query
time python main.py query "Your question?"

# Profile with cProfile
python -m cProfile -o profile.stats main.py query "test"
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('time').print_stats(20)"
```

### Monitor Resources
```bash
# CPU and memory
top -pid $(pgrep -f "run_server.py")

# Disk usage
du -sh data/ logs/

# Database connections
psql ecu_db -c "
  SELECT count(*) FROM pg_stat_activity
  WHERE datname = 'ecu_db';
"
```

---

## 🎯 Quick Workflows

### First Time Setup
```bash
./scripts/quickstart.sh
python scripts/verify_installation.py
python main.py interactive
```

### Daily Development
```bash
# Terminal 1: API
python scripts/run_server.py --reload

# Terminal 2: Web UI
cd web && python -m http.server 3000

# Terminal 3: Logs
tail -f logs/ecu_*.log
```

### Ingest New Data
```bash
python scripts/ingest_documents.py --directory /new/data --limit 1000
psql ecu_db -c "SELECT COUNT(*) FROM observations;"
```

### Deploy Update
```bash
git pull
pip install -r requirements.txt
docker-compose down
docker-compose up -d --build
```

---

## 💾 Backup & Restore

### Backup
```bash
# Full backup
pg_dump ecu_db | gzip > ecu_backup_$(date +%Y%m%d).sql.gz

# Data only
pg_dump -a ecu_db | gzip > ecu_data_$(date +%Y%m%d).sql.gz

# Schema only
pg_dump -s ecu_db > ecu_schema.sql
```

### Restore
```bash
# Full restore
gunzip -c ecu_backup_20231115.sql.gz | psql ecu_db_new

# Data only
gunzip -c ecu_data_20231115.sql.gz | psql ecu_db
```

---

## 🆘 Troubleshooting Commands

### Check Services
```bash
# PostgreSQL running?
pg_isready

# API running?
curl http://localhost:8000/

# Port in use?
lsof -i :8000
```

### Fix Common Issues
```bash
# Kill stuck server
pkill -f run_server.py

# Reset database
dropdb ecu_db && createdb ecu_db
python scripts/setup_database.py

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
```

---

## 📚 Help Commands

### Get Help
```bash
# Main CLI help
python main.py --help

# Ingestion help
python scripts/ingest_documents.py --help

# Server help
python scripts/run_server.py --help

# Check Python version
python --version

# Check PostgreSQL version
psql --version
```

---

**Quick Reference Card**

```
Setup:    ./scripts/quickstart.sh
Verify:   python scripts/verify_installation.py
Ingest:   python scripts/ingest_documents.py --limit 100
Query:    python main.py interactive
API:      python scripts/run_server.py
Web:      cd web && python -m http.server 3000
Test:     pytest tests/
Logs:     tail -f logs/ecu_*.log
Stats:    curl http://localhost:8000/stats
```

