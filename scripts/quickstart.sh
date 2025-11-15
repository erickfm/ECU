#!/bin/bash
# Quickstart script for ECU system

set -e

echo "======================================"
echo "ECU System Quickstart"
echo "======================================"
echo

# Check Python
echo "Checking Python version..."
python3 --version

# Check PostgreSQL
echo "Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Please install PostgreSQL 14+."
    echo "   macOS: brew install postgresql@14"
    echo "   Linux: sudo apt-get install postgresql-14"
    exit 1
fi
echo "✓ PostgreSQL found"

# Check for .env
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create one with:"
    echo "   OPENAI_API_KEY=your-key-here"
    echo "   DATABASE_URL=postgresql://localhost:5432/ecu_db"
    exit 1
fi
echo "✓ .env file found"

# Install dependencies
echo
echo "Installing Python dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Create database
echo
echo "Creating PostgreSQL database..."
if psql -lqt | cut -d \| -f 1 | grep -qw ecu_db; then
    echo "⚠ Database 'ecu_db' already exists. Skipping creation."
else
    createdb ecu_db
    echo "✓ Database created"
fi

# Setup schema
echo
echo "Setting up database schema..."
python scripts/setup_database.py
echo "✓ Schema created"

# Ingest sample documents
echo
echo "Ingesting sample documents (first 100 files)..."
python scripts/ingest_documents.py --limit 100
echo "✓ Sample documents ingested"

# Success
echo
echo "======================================"
echo "✓ ECU System Ready!"
echo "======================================"
echo
echo "Try it out:"
echo "  python main.py interactive"
echo
echo "Example queries:"
echo "  - What people are mentioned most frequently?"
echo "  - What did the oversight committee investigate?"
echo "  - Are there any contradictions in the documents?"
echo
echo "To ingest more documents:"
echo "  python scripts/ingest_documents.py --limit 1000"
echo

