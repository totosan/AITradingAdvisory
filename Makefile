.PHONY: help setup start stop restart logs clean test shell crypto crypto-interactive local-setup local-run local-test

# Default target - show help
help:
	@echo "🪙 Crypto Analysis Platform - Commands"
	@echo "======================================="
	@echo ""
	@echo "📦 Setup & Installation:"
	@echo "  make setup              Complete Docker setup"
	@echo "  make local-setup        Local Python environment setup"
	@echo "  make start              Start Docker services"
	@echo "  make stop               Stop Docker services"
	@echo "  make restart            Restart Docker services"
	@echo ""
	@echo "🚀 Running the Platform:"
	@echo "  make run                Run crypto analysis (Docker)"
	@echo "  make local-run          Run crypto analysis (local)"
	@echo "  make crypto-interactive Interactive mode (Docker)"
	@echo "  make local-crypto-interactive  Interactive mode (local)"
	@echo ""
	@echo "📊 Monitoring & Logs:"
	@echo "  make logs               View all Docker logs"
	@echo "  make logs-app           View application logs only"
	@echo "  make status             Check Docker service status"
	@echo ""
	@echo "🔧 Development & Testing:"
	@echo "  make shell              Open shell in Docker container"
	@echo "  make test               Test Docker setup"
	@echo "  make local-test         Test local setup"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean              Stop services and remove volumes"
	@echo "  make rebuild            Rebuild Docker containers"
	@echo "  make pull-model         Show Ollama model instructions"
	@echo ""


# ============================================================================
# Setup & Installation
# ============================================================================

setup:
	@echo "🚀 Running complete setup..."
	@./setup.sh
	@echo "✅ Setup complete! Use 'make start' to begin."

local-setup:
	@echo "🔧 Setting up local Python environment..."
	@python3 -m venv .venv
	@. .venv/bin/activate && pip install --upgrade pip
	@. .venv/bin/activate && pip install -e .
	@echo "✅ Local environment ready!"
	@echo ""
	@echo "To activate: source .venv/bin/activate"
	@echo "Then run: make local-run"

# ============================================================================
# Docker Service Management
# ============================================================================

start:
	@echo "🚀 Starting Docker services..."
	@docker-compose up -d
	@echo "✅ Services started successfully"
	@echo "Use 'make run' to start crypto analysis"

stop:
	@echo "🛑 Stopping Docker services..."
	@docker-compose down
	@echo "✅ Services stopped"

restart:
	@echo "🔄 Restarting Docker services..."
	@docker-compose restart
	@echo "✅ Services restarted"

status:
	@echo "📊 Docker Service Status:"
	@docker-compose ps

# ============================================================================
# Running the Platform
# ============================================================================

run:
	@echo "🪙 Starting Crypto Analysis Platform (Docker)..."
	@docker exec -it magentic-app uv run python src/main.py

local-run:
	@echo "🪙 Starting Crypto Analysis Platform (Local)..."
	@. .venv/bin/activate && python src/main.py

crypto-interactive:
	@echo "🪙 Starting Advanced Crypto Analysis (Docker)..."
	@docker exec -it magentic-app uv run python examples/crypto_analysis.py --mode interactive

local-crypto-interactive:
	@echo "🪙 Starting Advanced Crypto Analysis (Local)..."
	@. .venv/bin/activate && python examples/crypto_analysis.py --mode interactive

# ============================================================================
# Monitoring & Logs
# ============================================================================

logs:
	@echo "📋 Following all Docker logs (Ctrl+C to exit)..."
	@docker-compose logs -f

logs-app:
	@echo "📋 Following application logs (Ctrl+C to exit)..."
	@docker-compose logs -f magentic-app

# ============================================================================
# Development & Testing
# ============================================================================

shell:
	@echo "🐚 Opening shell in Docker container..."
	@docker exec -it magentic-app /bin/bash

test:
	@echo "🧪 Testing Docker setup..."
	@echo ""
	@echo "1️⃣ Checking Ollama connection..."
	@curl -s http://localhost:11434/api/tags > /dev/null && echo "   ✅ Ollama is responding" || echo "   ❌ Ollama not responding (run 'ollama serve')"
	@echo ""
	@echo "2️⃣ Checking Docker container..."
	@docker ps | grep -q magentic-app && echo "   ✅ Container is running" || echo "   ❌ Container not running (run 'make start')"
	@echo ""
	@echo "Setup status check complete!"

local-test:
	@echo "🧪 Testing local setup..."
	@. .venv/bin/activate && python verify_platform.py

# ============================================================================
# Maintenance
# ============================================================================

clean:
	@echo "🧹 Cleaning up Docker resources..."
	@docker-compose down -v
	@rm -rf outputs/*.html outputs/*.txt
	@echo "✅ Cleanup complete"

rebuild:
	@echo "🔨 Rebuilding Docker containers..."
	@docker-compose build --no-cache
	@docker-compose up -d
	@echo "✅ Rebuild complete"

pull-model:
	@echo "⬇️  To pull an Ollama model, run:"
	@echo ""
	@echo "  ollama pull gpt-oss:20b"
	@echo "  ollama pull llama3.2"
	@echo "  ollama pull deepseek-r1:1.5b"
	@echo ""
	@echo "Then update src/config.py with your chosen model."
