#!/bin/bash
set -e

echo "DrGoAi Development Startup"
echo "=========================="

mkdir -p logs data/embeddings

echo "Installing dependencies..."
pip install -q -r requirements.txt --break-system-packages 2>/dev/null || pip install -q -r requirements.txt

echo "Initializing database..."
python -c "from app.db.database import init_db; init_db()" || true

echo "Starting DrGoAi in development mode..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
