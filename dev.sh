#!/bin/bash

# Development environment manager - starts both Supabase and app services
# Press Ctrl+C to gracefully shut down everything

set -e

cleanup() {
    echo ""
    echo "🛑 Shutting down development environment..."
    docker-compose -f docker-compose-local.yml down
    supabase stop
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    echo "✅ Development environment stopped"
    exit 0
}

# Set up signal traps for graceful shutdown
trap cleanup SIGINT SIGTERM

echo "🚀 Starting development environment..."

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found."
    echo "   Install guide: https://supabase.com/docs/guides/local-development/cli/getting-started"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start Supabase local stack (background)
echo "📦 Starting Supabase services..."
supabase start

# Start frontend in background if it exists
if [ -d "web" ]; then
    echo "🎨 Starting frontend development server..."
    cd web && npm run dev &
    FRONTEND_PID=$!
    cd ..
fi

echo ""
echo "🏗️  Starting application services with live logs..."
echo "   Press Ctrl+C to stop everything"
echo ""

# Start docker-compose in foreground (shows logs, no -d flag)
docker-compose -f docker-compose-local.yml up --build
