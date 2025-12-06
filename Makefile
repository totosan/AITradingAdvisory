.PHONY: help setup start stop restart logs clean shell run local-setup local-run sync dev prod build test

# Default target - show help
help:
	@echo "🪙 AgenticTrades Crypto Analysis Platform"
	@echo "========================================"
	@echo ""
	@echo "🚀 Quick Start (from host terminal):"
	@echo "  make dev           Start with Docker (recommended)"
	@echo ""
	@echo "🖥️  Development:"
	@echo "  make dev           Docker mode (rebuilds on each run)"
	@echo "  make dev-local     Local mode (hot reload, for devcontainers)"
	@echo "  make dev-backend   Backend only (local)"
	@echo "  make dev-frontend  Frontend only (local)"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make prod          Production mode"
	@echo "  make build         Build Docker images"
	@echo "  make start         Start Docker services"
	@echo "  make stop          Stop all services"
	@echo "  make restart       Restart services"
	@echo "  make logs          View logs"
	@echo "  make status        Check container status"
	@echo ""
	@echo "📦 Setup:"
	@echo "  make setup         Complete Docker setup"
	@echo "  make local-setup   Local setup with UV"
	@echo "  make sync          Sync dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-unit     Run unit tests"
	@echo "  make test-api      Test API endpoints"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean         Stop services and clean outputs"
	@echo "  make rebuild       Rebuild Docker containers"
	@echo ""
	@echo "📚 URLs (when running):"
	@echo "  Frontend:  http://localhost:5173"
	@echo "  Backend:   http://localhost:8500"
	@echo "  API Docs:  http://localhost:8500/docs"
	@echo ""

# ============================================================================
# Setup (using UV)
# ============================================================================

setup:
	@echo "🚀 Running complete setup..."
	@./setup.sh
	@echo "✅ Setup complete! Use 'make dev' to start."

local-setup:
	@echo "🔧 Setting up local environment with UV..."
	@command -v uv >/dev/null 2>&1 || { echo "Installing UV..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	@uv venv
	@uv pip install -e .
	@echo "✅ Environment ready!"
	@echo "Run: make dev-local"

sync:
	@echo "📦 Syncing dependencies..."
	@uv pip install -e .
	@echo "✅ Dependencies synced"

# ============================================================================
# Docker Service Management
# ============================================================================

# Development mode with Docker (rebuilds image on each run)
dev:
	@echo "🔧 Starting development mode (Docker)..."
	@docker-compose -f docker-compose.dev.yml up --build
	@echo "📍 Frontend: http://localhost:5173"
	@echo "📍 Backend:  http://localhost:8500"

# Development mode without Docker (ideal for devcontainers)
# Runs services directly with hot reload
dev-local:
	@echo "🔧 Starting local development mode..."
	@echo "📍 Frontend: http://localhost:5173"
	@echo "📍 Backend:  http://localhost:8500"
	@echo ""
	@echo "Starting backend and frontend in parallel..."
	@(trap 'kill 0' SIGINT; \
		(cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8500 --reload) & \
		(cd frontend && npm install && npm run dev -- --host 0.0.0.0) & \
		wait)

# Backend only (local, with hot reload)
dev-backend:
	@echo "🔧 Starting backend..."
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8500 --reload

# Frontend only (local, with hot reload)
dev-frontend:
	@echo "🔧 Starting frontend..."
	cd frontend && npm install && npm run dev -- --host 0.0.0.0

# Production mode
prod:
	@echo "🚀 Starting production mode..."
	@docker-compose -f docker-compose.prod.yml up -d --build
	@echo "✅ Production services started"
	@echo "📍 Frontend: http://localhost:80"
	@echo "📍 Backend:  http://localhost:8500"

# Build Docker images
build:
	@echo "🔨 Building Docker images..."
	@docker-compose -f docker-compose.prod.yml build
	@echo "✅ Build complete"

start:
	@echo "🚀 Starting Docker services..."
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Services started"

stop:
	@docker-compose -f docker-compose.prod.yml down
	@docker-compose -f docker-compose.dev.yml down 2>/dev/null || true

restart:
	@docker-compose -f docker-compose.prod.yml restart

status:
	@docker-compose -f docker-compose.prod.yml ps

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
	@docker-compose -f docker-compose.prod.yml logs -f

logs-dev:
	@docker-compose -f docker-compose.dev.yml logs -f

shell:
	@docker exec -it magentic-backend /bin/sh

shell-frontend:
	@docker exec -it magentic-frontend /bin/sh

# ============================================================================
# Testing
# ============================================================================

test:
	@echo "🧪 Running all tests..."
	@cd /workspaces/MagenticOne && .venv/bin/pytest tests/ -v
	@echo "✅ All tests passed"

test-unit:
	@echo "🧪 Running unit tests..."
	@cd /workspaces/MagenticOne && .venv/bin/pytest tests/ -v --tb=short

test-api:
	@echo "🧪 Testing API endpoints..."
	@curl -s http://localhost:8500/api/v1/health | python3 -m json.tool
	@curl -s http://localhost:8500/api/v1/health/ready | python3 -m json.tool
	@echo "✅ API tests passed"

# ============================================================================
# Maintenance
# ============================================================================

clean:
	@echo "🧹 Cleaning up..."
	@docker-compose -f docker-compose.prod.yml down -v 2>/dev/null || true
	@docker-compose -f docker-compose.dev.yml down -v 2>/dev/null || true
	@rm -rf outputs/*/*.html outputs/*/*.txt outputs/*/*.md
	@echo "✅ Cleanup complete"

rebuild:
	@echo "🔨 Rebuilding Docker containers..."
	@docker-compose -f docker-compose.prod.yml build --no-cache
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Rebuild complete"
