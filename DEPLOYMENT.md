# ECU System Deployment Guide

Complete guide for deploying the Emergent Corpus Understanding system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Database Setup](#database-setup)
4. [Document Ingestion](#document-ingestion)
5. [Running the System](#running-the-system)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python 3.9+**
- **PostgreSQL 14+** with pgvector extension
- **OpenAI API Key** (or use local embeddings)

### Operating System

- macOS, Linux, or Windows (WSL recommended)

### Hardware Recommendations

- **Minimum**: 8GB RAM, 20GB disk space
- **Recommended**: 16GB+ RAM, 100GB+ disk space (for large corpora)
- **GPU**: Optional, but recommended for local embeddings

## Local Development Setup

### 1. Clone and Install

```bash
cd /Users/erick/ECU

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# OpenAI (required for now)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Database
DATABASE_URL=postgresql://localhost:5432/ecu_db

# Agent Configuration
MAX_ITERATIONS=15
CONFIDENCE_THRESHOLD=0.8
SEMANTIC_SEARCH_K=20

# Data Path
DATA_DIR=/Users/erick/Downloads/all-ocr-text
```

## Database Setup

### Install PostgreSQL

**macOS:**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql-14 postgresql-contrib-14
sudo systemctl start postgresql
```

### Install pgvector Extension

```bash
# macOS
brew install pgvector

# Ubuntu/Debian
sudo apt-get install postgresql-14-pgvector

# Or build from source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### Create Database

```bash
# Create database
createdb ecu_db

# Initialize schema
python scripts/setup_database.py
```

**Expected output:**
```
Setting up database: postgresql://localhost:5432/ecu_db
Database setup complete!
Tables created: observations, observation_cooccurrence, cached_hypotheses, query_sessions
```

### Verify Setup

```bash
psql ecu_db -c "\d observations"
```

Should show the observations table schema.

## Document Ingestion

### Quick Start (First 100 Documents)

```bash
python scripts/ingest_documents.py --limit 100
```

### Full Ingestion

For the full corpus (~23,000 documents):

```bash
# This will take 20-60 minutes depending on hardware
python scripts/ingest_documents.py

# With progress tracking
python scripts/ingest_documents.py 2>&1 | tee ingestion.log
```

### Custom Directory

```bash
python scripts/ingest_documents.py --directory /path/to/documents --limit 1000
```

### Monitoring Ingestion

```bash
# Check observation count
psql ecu_db -c "SELECT COUNT(*) FROM observations;"

# Check co-occurrence count
psql ecu_db -c "SELECT COUNT(*) FROM observation_cooccurrence;"
```

## Running the System

### Option 1: Interactive CLI

```bash
python main.py interactive
```

Example session:
```
Query> Who is Jeffrey Epstein?
[System processes query...]
ANSWER: Jeffrey Epstein was a financier and convicted sex offender...
CONFIDENCE: 8.5/10
ITERATIONS: 3
OBSERVATIONS: 45
```

### Option 2: Single Query

```bash
python main.py query "What organizations are mentioned in the documents?"
```

### Option 3: API Server + Web UI

**Terminal 1 - Start API:**
```bash
python scripts/run_server.py
```

**Terminal 2 - Serve Web UI:**
```bash
cd web
python -m http.server 3000
```

**Access:**
- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs

### Option 4: Programmatic Usage

```python
from sqlalchemy import create_engine
from src.agent import ECUAgent
from src.config import config

engine = create_engine(config.DATABASE_URL)
agent = ECUAgent(engine)

result = agent.query("Your question here")
print(result['answer'])
```

## Production Deployment

### Docker Deployment (Recommended)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run
CMD ["python", "scripts/run_server.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg14
    environment:
      POSTGRES_DB: ecu_db
      POSTGRES_USER: ecu
      POSTGRES_PASSWORD: your_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  api:
    build: .
    environment:
      DATABASE_URL: postgresql://ecu:your_password@db:5432/ecu_db
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs

volumes:
  pgdata:
```

**Deploy:**
```bash
docker-compose up -d
```

### AWS Deployment

**Using AWS RDS + EC2:**

1. **Create RDS PostgreSQL instance** with pgvector
2. **Launch EC2 instance** (t3.medium or larger)
3. **Install dependencies** on EC2
4. **Configure** DATABASE_URL to RDS endpoint
5. **Run ingestion** from EC2
6. **Start API server** with systemd

Example systemd service (`/etc/systemd/system/ecu-api.service`):

```ini
[Unit]
Description=ECU API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ECU
Environment="PATH=/home/ubuntu/ECU/venv/bin"
ExecStart=/home/ubuntu/ECU/venv/bin/python scripts/run_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ecu-api
sudo systemctl start ecu-api
```

### Cloud Database Options

**Managed PostgreSQL with pgvector:**
- AWS RDS (requires pgvector manual install)
- Google Cloud SQL
- Azure Database for PostgreSQL
- Supabase (native pgvector support)
- Neon.tech (native pgvector support)

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql postgresql://localhost:5432/ecu_db

# Check PostgreSQL is running
pg_isready

# Restart PostgreSQL
brew services restart postgresql@14  # macOS
sudo systemctl restart postgresql    # Linux
```

### pgvector Extension Not Found

```bash
# Verify extension is installed
psql ecu_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# If error, reinstall pgvector
brew reinstall pgvector  # macOS
```

### Out of Memory During Ingestion

Reduce batch size in `src/ingestion/document_processor.py`:

```python
batch_size = 50  # Change from 100 to 50
```

Or process in chunks:
```bash
python scripts/ingest_documents.py --limit 1000
# Wait for completion, then:
python scripts/ingest_documents.py --limit 2000
# etc.
```

### Slow Query Performance

```bash
# Check index creation
psql ecu_db -c "\d observations"

# Rebuild indices if needed
psql ecu_db -c "REINDEX TABLE observations;"

# Analyze tables
psql ecu_db -c "ANALYZE observations;"
```

### OpenAI Rate Limits

Add retry logic or use local embeddings:

In `.env`:
```
USE_LOCAL_EMBEDDINGS=true
```

### API Server Won't Start

```bash
# Check port availability
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Use different port
python scripts/run_server.py --port 8080
```

## Performance Optimization

### Database Tuning

Add to `postgresql.conf`:

```
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 16MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
```

### Query Optimization

Increase `SEMANTIC_SEARCH_K` for better recall:
```python
SEMANTIC_SEARCH_K=50  # Default is 20
```

Reduce `MAX_ITERATIONS` for faster responses:
```python
MAX_ITERATIONS=10  # Default is 15
```

## Monitoring

### Logs

```bash
# View logs
tail -f logs/ecu_*.log

# Search errors
grep ERROR logs/ecu_*.log
```

### Metrics Endpoint

```bash
curl http://localhost:8000/stats
```

Returns:
```json
{
  "observations_count": 125000,
  "sessions_count": 150,
  "avg_confidence": 7.8,
  "avg_iterations": 6.2
}
```

### Database Stats

```sql
-- Observation count by doc_id
SELECT 
    LEFT(doc_id, 20) as doc_prefix,
    COUNT(*) as count
FROM observations
GROUP BY doc_prefix
ORDER BY count DESC
LIMIT 10;

-- Average confidence by session
SELECT 
    AVG(confidence_score) as avg_confidence,
    AVG(iterations) as avg_iterations
FROM query_sessions
WHERE status = 'completed';
```

## Backup and Restore

### Backup

```bash
# Dump database
pg_dump ecu_db > ecu_backup_$(date +%Y%m%d).sql

# Compress
gzip ecu_backup_$(date +%Y%m%d).sql
```

### Restore

```bash
# Create database
createdb ecu_db_restore

# Restore
gunzip -c ecu_backup_20231115.sql.gz | psql ecu_db_restore
```

## Security Considerations

1. **API Key Protection**
   - Never commit `.env` to git
   - Use environment variables in production
   - Rotate keys regularly

2. **Database Security**
   - Use strong passwords
   - Restrict network access
   - Enable SSL connections

3. **API Security**
   - Add authentication (JWT, API keys)
   - Rate limiting
   - CORS configuration

4. **Data Privacy**
   - Encrypt sensitive data
   - Log sanitization
   - Access controls

## Next Steps

- [ ] Set up automated backups
- [ ] Configure monitoring/alerting
- [ ] Add authentication to API
- [ ] Set up CI/CD pipeline
- [ ] Scale horizontally with load balancer
- [ ] Implement caching layer (Redis)
- [ ] Add observability (Prometheus, Grafana)

## Support

For issues or questions:
- Check logs: `logs/ecu_*.log`
- Review spec: `emergent-corpus-understanding-spec.md`
- GitHub Issues: [Create issue]

