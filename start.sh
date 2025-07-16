#!/bin/bash
set -e

source .venv/bin/activate

# Function to cleanup background processes
cleanup() {
    echo "Shutting down..."
    if [[ -n "$FLOWER_PID" ]]; then
        kill $FLOWER_PID 2>/dev/null || true
        wait $FLOWER_PID 2>/dev/null || true
    fi
    if [[ -n "$WORKER_PID" ]]; then
        kill $WORKER_PID 2>/dev/null || true
        wait $WORKER_PID 2>/dev/null || true
    fi
    exit 0
}

# [TODO] remove this
mkdir -p /tmp/dwell

trap cleanup SIGINT SIGTERM

echo "Starting Celery worker and Flower..."
echo "Starting Flower monitoring UI on port 5555..."
celery -A src.workers.tasks flower --port=5555 &
FLOWER_PID=$!

echo "Starting Celery worker..."
celery -A src.workers.tasks worker --loglevel=info --concurrency=2 &
WORKER_PID=$!

# Wait for either process to exit
wait
