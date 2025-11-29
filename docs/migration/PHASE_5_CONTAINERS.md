# Phase 5: Containerization & Azure Preparation

## Overview

Finalize Docker setup and prepare for Azure Container Apps deployment.

---

## 5.1 Final Project Structure

```
MagenticOne/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py
│   │   │   │   ├── charts.py
│   │   │   │   ├── settings.py
│   │   │   │   └── health.py
│   │   │   └── websocket/
│   │   │       ├── __init__.py
│   │   │       └── stream.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── agent_service.py
│   │   │   └── chart_service.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── requests.py
│   │   │   ├── responses.py
│   │   │   └── events.py
│   │   └── utils/
│   │       └── __init__.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
│
├── frontend/
│   ├── src/
│   │   └── (React app)
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .dockerignore
│
├── src/                         # Existing agent code (mounted)
│   ├── config.py
│   ├── crypto_tools.py
│   └── ...
│
├── docker-compose.yml           # Production
├── docker-compose.dev.yml       # Development
├── docker-compose.override.yml  # Local overrides
├── Makefile                     # Updated with new commands
│
├── azure/
│   ├── bicep/
│   │   ├── main.bicep
│   │   ├── containerApp.bicep
│   │   └── parameters.json
│   └── deploy.sh
│
└── docs/migration/              # This documentation
```

---

## 5.2 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Dependencies Stage ----
FROM base as dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Production Stage ----
FROM dependencies as production

# Copy existing agent code
COPY ../src /app/src

# Copy backend application
COPY app /app/app

# Create non-root user
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data /app/outputs \
    && chown -R appuser:appuser /app

USER appuser

# Create output directories
RUN mkdir -p /app/outputs/charts /app/outputs/reports /app/outputs/code_execution

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---- Development Stage ----
FROM dependencies as development

# Install dev dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio httpx

# Copy code (will be overridden by volume mount in dev)
COPY ../src /app/src
COPY app /app/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

```txt
# backend/.dockerignore
__pycache__
*.pyc
*.pyo
*.pyd
.Python
.env
.venv
venv/
ENV/
.git
.gitignore
.pytest_cache
.mypy_cache
*.egg-info
dist/
build/
.coverage
htmlcov/
.tox
.eggs
docs/
tests/
*.md
!requirements.txt
```

---

## 5.3 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile

# ---- Build Stage ----
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .

# Build with production API URL (will be overridden at runtime)
ARG VITE_API_URL=http://localhost:8000
ARG VITE_WS_URL=ws://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build

# ---- Production Stage ----
FROM nginx:alpine as production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create script to inject runtime environment variables
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
```

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml application/javascript;

    # SPA routing - all routes to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Static chart files
    location /charts {
        proxy_pass http://backend:8000/charts;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

```bash
#!/bin/sh
# frontend/docker-entrypoint.sh

# Replace environment variables in the built JS files
# This allows runtime configuration without rebuilding

# Find and replace placeholders
find /usr/share/nginx/html -type f -name "*.js" -exec sed -i \
    -e "s|VITE_API_URL_PLACEHOLDER|${VITE_API_URL:-http://localhost:8000}|g" \
    -e "s|VITE_WS_URL_PLACEHOLDER|${VITE_WS_URL:-ws://localhost:8000}|g" \
    {} \;

exec "$@"
```

---

## 5.4 Docker Compose (Production)

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
      target: production
    container_name: crypto-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      # Persistent secrets storage
      - secrets-data:/app/data
      # Output files (charts, reports)
      - ./outputs:/app/outputs
    environment:
      - PYTHONPATH=/app/src:/app
      - SECRETS_DIR=/app/data
      - OUTPUT_DIR=/app/outputs
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
      - OLLAMA_MODEL=${OLLAMA_MODEL:-gpt-oss:20b}
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT:-}
      - AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT:-gpt-4o}
      - CORS_ORIGINS=http://localhost:3000,http://localhost
      - MAX_TURNS=${MAX_TURNS:-20}
      - MAX_STALLS=${MAX_STALLS:-3}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - crypto-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    container_name: crypto-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - crypto-network

networks:
  crypto-network:
    driver: bridge

volumes:
  secrets-data:
    name: crypto-secrets
```

---

## 5.5 Docker Compose (Development)

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
      target: development
    container_name: crypto-backend-dev
    ports:
      - "8000:8000"
    volumes:
      # Mount source for hot reload
      - ./src:/app/src:ro
      - ./backend/app:/app/app
      - secrets-data:/app/data
      - ./outputs:/app/outputs
    environment:
      - PYTHONPATH=/app/src:/app
      - DEBUG=true
      - SECRETS_DIR=/app/data
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    networks:
      - crypto-network-dev

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: builder  # Use builder stage for dev
    container_name: crypto-frontend-dev
    ports:
      - "3000:5173"
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000
    command: npm run dev -- --host 0.0.0.0
    depends_on:
      - backend
    networks:
      - crypto-network-dev

  # Optional: Local Ollama
  ollama:
    image: ollama/ollama:latest
    container_name: crypto-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    profiles:
      - with-ollama
    networks:
      - crypto-network-dev

networks:
  crypto-network-dev:
    driver: bridge

volumes:
  secrets-data:
  ollama-models:
```

---

## 5.6 Updated Makefile

```makefile
# Makefile
.PHONY: help build start stop dev logs clean test

# Default target
help:
	@echo "🪙 Crypto Analysis Platform - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Start development environment"
	@echo "  make dev-build     - Rebuild and start development"
	@echo "  make logs          - View container logs"
	@echo "  make logs-backend  - View backend logs only"
	@echo "  make logs-frontend - View frontend logs only"
	@echo ""
	@echo "Production:"
	@echo "  make build         - Build production containers"
	@echo "  make start         - Start production containers"
	@echo "  make stop          - Stop all containers"
	@echo "  make restart       - Restart all containers"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-backend  - Run backend tests"
	@echo "  make test-frontend - Run frontend tests"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         - Remove containers and volumes"
	@echo "  make shell-backend - Shell into backend container"
	@echo "  make shell-frontend- Shell into frontend container"
	@echo ""
	@echo "Azure:"
	@echo "  make azure-deploy  - Deploy to Azure Container Apps"
	@echo "  make azure-logs    - View Azure logs"

# ==================== Development ====================

dev:
	docker-compose -f docker-compose.dev.yml up

dev-build:
	docker-compose -f docker-compose.dev.yml up --build

dev-with-ollama:
	docker-compose -f docker-compose.dev.yml --profile with-ollama up

# ==================== Production ====================

build:
	docker-compose build

start:
	docker-compose up -d

stop:
	docker-compose down

restart:
	docker-compose restart

# ==================== Logs ====================

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

# ==================== Testing ====================

test: test-backend test-frontend

test-backend:
	docker-compose -f docker-compose.dev.yml run --rm backend pytest

test-frontend:
	docker-compose -f docker-compose.dev.yml run --rm frontend npm test

# ==================== Utilities ====================

clean:
	docker-compose down -v --remove-orphans
	docker-compose -f docker-compose.dev.yml down -v --remove-orphans
	docker system prune -f

shell-backend:
	docker-compose exec backend /bin/bash

shell-frontend:
	docker-compose exec frontend /bin/sh

# ==================== Azure ====================

azure-login:
	az login
	az acr login --name cryptoanalysis

azure-build:
	docker build -t cryptoanalysis.azurecr.io/backend:latest -f backend/Dockerfile .
	docker build -t cryptoanalysis.azurecr.io/frontend:latest frontend/

azure-push:
	docker push cryptoanalysis.azurecr.io/backend:latest
	docker push cryptoanalysis.azurecr.io/frontend:latest

azure-deploy: azure-build azure-push
	az deployment group create \
		--resource-group crypto-analysis-rg \
		--template-file azure/bicep/main.bicep \
		--parameters @azure/bicep/parameters.json

azure-logs:
	az containerapp logs show \
		--name crypto-backend \
		--resource-group crypto-analysis-rg \
		--follow
```

---

## 5.7 Azure Bicep Templates

```bicep
// azure/bicep/main.bicep
targetScope = 'resourceGroup'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Container App Environment name')
param environmentName string = 'crypto-analysis-env'

@description('Container Registry name')
param acrName string = 'cryptoanalysis'

@description('Backend image tag')
param backendImageTag string = 'latest'

@description('Frontend image tag')
param frontendImageTag string = 'latest'

// Container App Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${environmentName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Backend Container App
resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'crypto-backend'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
      }
      secrets: [
        {
          name: 'azure-openai-key'
          value: '' // Set via Azure Key Vault reference
        }
      ]
      registries: [
        {
          server: '${acrName}.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${acrName}.azurecr.io/backend:${backendImageTag}'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'LLM_PROVIDER'
              value: 'azure'
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-key'
            }
            {
              name: 'SECRETS_DIR'
              value: '/app/data'
            }
          ]
          volumeMounts: [
            {
              volumeName: 'secrets-volume'
              mountPath: '/app/data'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
      volumes: [
        {
          name: 'secrets-volume'
          storageType: 'AzureFile'
          storageName: 'secrets-storage'
        }
      ]
    }
  }
}

// Frontend Container App
resource frontendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'crypto-frontend'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
        customDomains: []
      }
      registries: [
        {
          server: '${acrName}.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${acrName}.azurecr.io/frontend:${frontendImageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'VITE_API_URL'
              value: 'https://${backendApp.properties.configuration.ingress.fqdn}'
            }
            {
              name: 'VITE_WS_URL'
              value: 'wss://${backendApp.properties.configuration.ingress.fqdn}'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
```

---

## 5.8 Azure Deployment Script

```bash
#!/bin/bash
# azure/deploy.sh

set -e

# Configuration
RESOURCE_GROUP="crypto-analysis-rg"
LOCATION="eastus"
ACR_NAME="cryptoanalysis"
ENVIRONMENT_NAME="crypto-analysis-env"

echo "🚀 Deploying Crypto Analysis Platform to Azure..."

# 1. Login to Azure (if needed)
if ! az account show > /dev/null 2>&1; then
    echo "📝 Please login to Azure..."
    az login
fi

# 2. Create Resource Group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# 3. Create Container Registry
echo "🐳 Creating container registry..."
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true

# 4. Build and push images
echo "🏗️ Building and pushing images..."
az acr login --name $ACR_NAME

docker build -t $ACR_NAME.azurecr.io/backend:latest -f backend/Dockerfile .
docker build -t $ACR_NAME.azurecr.io/frontend:latest frontend/

docker push $ACR_NAME.azurecr.io/backend:latest
docker push $ACR_NAME.azurecr.io/frontend:latest

# 5. Deploy with Bicep
echo "☁️ Deploying to Azure Container Apps..."
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file azure/bicep/main.bicep \
    --parameters acrName=$ACR_NAME \
    --parameters location=$LOCATION

# 6. Get URLs
FRONTEND_URL=$(az containerapp show \
    --name crypto-frontend \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    --output tsv)

echo ""
echo "✅ Deployment complete!"
echo "🌐 Frontend URL: https://$FRONTEND_URL"
echo ""
echo "📊 To view logs:"
echo "   az containerapp logs show --name crypto-backend --resource-group $RESOURCE_GROUP --follow"
```

---

## 5.9 Environment Variables Reference

```bash
# .env.example

# ===================
# LLM Configuration
# ===================
LLM_PROVIDER=ollama                    # ollama or azure

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# ===================
# Agent Configuration
# ===================
MAX_TURNS=20
MAX_STALLS=3

# ===================
# Application
# ===================
DEBUG=false
OUTPUT_DIR=outputs
SECRETS_DIR=/app/data
CORS_ORIGINS=http://localhost:3000

# ===================
# Exchange (set via UI)
# ===================
# BITGET_API_KEY=       # Set via settings UI
# BITGET_API_SECRET=    # Set via settings UI
# BITGET_PASSPHRASE=    # Set via settings UI
```

---

## 5.10 Health Check Endpoints

```python
# backend/app/api/routes/health.py (complete)
"""
Health check endpoints for container orchestration.
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends
import httpx

from app.core.config import Settings, get_settings
from app.core.security import SecretsVault, get_vault

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check - confirms API is responding.
    Used by load balancers for quick checks.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


@router.get("/health/ready")
async def readiness_check(
    settings: Settings = Depends(get_settings),
    vault: SecretsVault = Depends(get_vault),
) -> Dict[str, Any]:
    """
    Readiness check - verifies all dependencies are available.
    Container won't receive traffic until this passes.
    """
    checks = {
        "api": True,
        "secrets_vault": vault.key_file.exists(),
    }
    
    # Check LLM provider
    if settings.llm_provider == "ollama":
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.ollama_base_url}/api/tags",
                    timeout=5.0
                )
                checks["ollama"] = resp.status_code == 200
        except Exception:
            checks["ollama"] = False
    
    elif settings.llm_provider == "azure":
        # Check if Azure key is configured
        checks["azure_openai"] = bool(
            settings.azure_openai_api_key or 
            vault.has_secret("azure_openai_api_key")
        )
    
    # Overall status
    all_healthy = all(v for v in checks.values() if isinstance(v, bool))
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check - confirms process is running.
    If this fails, container will be restarted.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/startup")
async def startup_check(
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """
    Startup check - used during initial container startup.
    Allows more time for initialization.
    """
    return {
        "status": "started",
        "provider": settings.llm_provider,
        "timestamp": datetime.now().isoformat(),
    }
```

---

## 5.11 Checklist Before Deployment

### Pre-deployment Checklist

- [ ] All tests passing
- [ ] Docker images build successfully
- [ ] Health endpoints responding
- [ ] WebSocket connection working
- [ ] Charts rendering correctly
- [ ] Settings saving/loading
- [ ] Secrets encryption verified

### Azure Deployment Checklist

- [ ] Azure CLI installed and logged in
- [ ] Resource group created
- [ ] Container Registry created
- [ ] Images pushed to ACR
- [ ] Bicep templates validated
- [ ] Environment variables set
- [ ] Custom domain configured (optional)
- [ ] SSL certificates provisioned
- [ ] Monitoring enabled

---

## Completion Summary

You now have a complete plan for:

1. **Backend API** - FastAPI with WebSocket support
2. **Frontend** - React + TypeScript with TradingView charts
3. **Real-time** - WebSocket communication with reconnection
4. **Secrets** - Encrypted storage with Fernet
5. **Containers** - Docker Compose for local, Azure Container Apps for cloud

---

*Document created: 2025-11-29*
