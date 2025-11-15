#!/bin/bash
echo "Starting DrGoAi Pre-Authorization System..."
echo "Installing dependencies..."
pip install -r requirements.txt --break-system-packages 2>/dev/null || pip install -r requirements.txt
echo "Starting server..."
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
