#!/bin/bash
set -e

echo "DrGoAi Production Startup"
echo "=========================="

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Create necessary directories
mkdir -p logs data/embeddings

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Initialize database
echo "Initializing database..."
python -c "from app.db.database import init_db; init_db()" || true

# Start application with Gunicorn for production
echo "Starting DrGoAi in production mode..."
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info \
    --timeout 300 \
    --keep-alive 5
