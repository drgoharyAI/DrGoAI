#!/bin/bash
# DrGoAi - HuggingFace Spaces Startup Script

# Get PORT from environment (default to 7860 for HF Spaces)
PORT=${PORT:-7860}
HOST=${HOST:-0.0.0.0}

echo "🚀 Starting DrGoAi on $HOST:$PORT"
echo "Environment: HuggingFace Spaces"

# Start with uvicorn
uvicorn app.main:app \
    --host $HOST \
    --port $PORT \
    --reload \
    --log-level info \
    --access-log
