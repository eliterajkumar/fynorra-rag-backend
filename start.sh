#!/bin/bash
# Fynorra RAG Backend - Development Startup Script

set -e

echo "🚀 Starting Fynorra RAG Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "🔴 Redis not running. Please start Redis first:"
    echo "   sudo systemctl start redis"
    echo "   OR: redis-server"
    exit 1
fi

# Initialize database
echo "🗄️ Initializing database..."
python3 migrations/0001_create_tables.py

# Start services in background
echo "🌐 Starting Flask app..."
python3 src/app.py &
FLASK_PID=$!

echo "⚙️ Starting Celery worker..."
celery -A src.tasks.celery_app worker --loglevel=info &
CELERY_PID=$!

echo "✅ Services started!"
echo "📍 Flask API: http://localhost:5000"
echo "📍 Health check: http://localhost:5000/health"
echo ""
echo "🛑 To stop services:"
echo "   kill $FLASK_PID $CELERY_PID"
echo ""
echo "📋 Service PIDs:"
echo "   Flask: $FLASK_PID"
echo "   Celery: $CELERY_PID"

# Wait for user input to stop
echo "Press Ctrl+C to stop all services..."
trap "echo '🛑 Stopping services...'; kill $FLASK_PID $CELERY_PID 2>/dev/null; exit 0" INT

# Keep script running
wait
