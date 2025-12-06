#!/bin/bash
# Quick Start Script for AITradingAdvisory Web Platform
# Run this in a fresh terminal to start the system

set -e  # Exit on error

echo "🚀 Starting AITradingAdvisory Web Platform"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from project root (/workspaces/MagenticOne)"
    exit 1
fi

# Check Python virtual environment
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    uv venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if required packages are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing backend dependencies..."
    uv pip install -q fastapi uvicorn websockets pydantic pydantic-settings httpx
fi

# Start backend
echo ""
echo "🌐 Starting backend on http://0.0.0.0:8500"
echo "   WebSocket: ws://0.0.0.0:8500/ws/stream"
echo "   Access from host: http://localhost:8500"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

cd backend
PYTHONPATH=/workspaces/MagenticOne/backend python -m uvicorn app.main:app --host 0.0.0.0 --port 8500
