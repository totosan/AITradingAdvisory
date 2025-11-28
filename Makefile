.PHONY: help setup start stop restart logs clean shell run local-setup local-run sync

# Default target - show help
help:
	@echo "🪙 Crypto Analysis Platform"
	@echo "==========================="
	@echo ""
	@echo "📦 Setup:"
	@echo "  make setup       Complete Docker setup"
	@echo "  make local-setup Local setup with UV"
	@echo "  make sync        Sync dependencies (UV)"
	@echo ""
	@echo "🚀 Running:"
	@echo "  make run         Run platform (Docker)"
	@echo "  make local-run   Run platform (local)"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make start       Start Docker services"
	@echo "  make stop        Stop Docker services"
	@echo "  make restart     Restart Docker services"
	@echo "  make logs        View Docker logs"
	@echo "  make shell       Open shell in container"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean       Stop services and clean outputs"
	@echo "  make rebuild     Rebuild Docker containers"
	@echo ""

# ============================================================================
# Setup (using UV)
# ============================================================================

setup:
	@echo "🚀 Running complete setup..."
	@./setup.sh
	@echo "✅ Setup complete! Use 'make start' to begin."

local-setup:
	@echo "🔧 Setting up local environment with UV..."
	@command -v uv >/dev/null 2>&1 || { echo "Installing UV..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	@uv venv
	@uv pip install -e .
	@echo "✅ Environment ready!"
	@echo "Run: make local-run"

sync:
	@echo "📦 Syncing dependencies..."
	@uv pip install -e .
	@echo "✅ Dependencies synced"

# ============================================================================
# Docker Service Management
# ============================================================================

start:
	@echo "🚀 Starting Docker services..."
	@docker-compose up -d
	@echo "✅ Services started. Use 'make run' to start."

stop:
	@docker-compose down

restart:
	@docker-compose restart

status:
	@docker-compose ps

# ============================================================================
# Running the Platform
# ============================================================================

run:
	@docker exec -it magentic-app uv run python src/main.py

local-run:
	@PYTHONPATH=src uv run python src/main.py

# ============================================================================
# Monitoring & Development
# ============================================================================

logs:
	@docker-compose logs -f

shell:
	@docker exec -it magentic-app /bin/bash

# ============================================================================
# Maintenance
# ============================================================================

clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v 2>/dev/null || true
	@rm -rf outputs/*/*.html outputs/*/*.txt outputs/*/*.md
	@echo "✅ Cleanup complete"

rebuild:
	@echo "🔨 Rebuilding Docker containers..."
	@docker-compose build --no-cache
	@docker-compose up -d
	@echo "✅ Rebuild complete"
