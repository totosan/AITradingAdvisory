#!/bin/bash
# AgenticTrades Azure Deployment Script
# Deploys the application to Azure Container Apps using Bicep
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Docker installed and running
#   - .env file with Azure OpenAI credentials
#
# Usage:
#   ./deploy.sh                    # Deploy with defaults
#   ./deploy.sh --app-name myapp   # Deploy with custom app name
#   ./deploy.sh --help             # Show help

set -e

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
APP_NAME="magentic-one"
LOCATION="swedencentral"
IMAGE_TAG="latest"

# ============================================================================
# Functions
# ============================================================================

show_help() {
    echo "AgenticTrades Azure Deployment"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --app-name NAME       Application name (default: magentic-one)"
    echo "  --location LOCATION   Azure region (default: swedencentral)"
    echo "  --tag TAG             Docker image tag (default: latest)"
    echo "  --help                Show this help message"
    echo ""
    echo "Environment variables (from .env or exported):"
    echo "  AZURE_OPENAI_ENDPOINT     Azure OpenAI endpoint URL"
    echo "  AZURE_OPENAI_API_KEY      Azure OpenAI API key"
    echo "  AZURE_OPENAI_DEPLOYMENT   Azure OpenAI deployment name"
    echo "  BITGET_API_KEY            (optional) Bitget API key"
    echo "  BITGET_API_SECRET         (optional) Bitget API secret"
    echo "  BITGET_PASSPHRASE         (optional) Bitget passphrase"
    echo ""
}

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[ERROR] $1" >&2
    exit 1
}

# ============================================================================
# Parse Arguments
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --app-name)
            APP_NAME="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# ============================================================================
# Load Environment
# ============================================================================

log "Loading environment..."

if [[ -f "$PROJECT_ROOT/.env" ]]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    log "Loaded .env file"
fi

# Validate required variables
if [[ -z "$AZURE_OPENAI_ENDPOINT" ]]; then
    error "AZURE_OPENAI_ENDPOINT is required"
fi
if [[ -z "$AZURE_OPENAI_API_KEY" ]]; then
    error "AZURE_OPENAI_API_KEY is required"
fi

# ============================================================================
# Azure Login Check
# ============================================================================

log "Checking Azure CLI login..."
if ! az account show &>/dev/null; then
    error "Please login to Azure first: az login"
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
log "Using subscription: $SUBSCRIPTION"

# ============================================================================
# Build and Push Docker Images
# ============================================================================

ACR_NAME="${APP_NAME//\-/}acr"
RG_NAME="rg-${APP_NAME}"

log "Creating resource group if not exists..."
az group create --name "$RG_NAME" --location "$LOCATION" --output none 2>/dev/null || true

log "Creating container registry if not exists..."
az acr create \
    --resource-group "$RG_NAME" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true \
    --output none 2>/dev/null || true

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
log "ACR Login Server: $ACR_LOGIN_SERVER"

log "Logging into container registry..."
az acr login --name "$ACR_NAME"

log "Building and pushing backend image..."
docker build \
    -f "$PROJECT_ROOT/backend/Dockerfile" \
    -t "$ACR_LOGIN_SERVER/${APP_NAME}-backend:${IMAGE_TAG}" \
    "$PROJECT_ROOT"
docker push "$ACR_LOGIN_SERVER/${APP_NAME}-backend:${IMAGE_TAG}"

log "Building and pushing frontend image..."
docker build \
    -f "$PROJECT_ROOT/frontend/Dockerfile" \
    -t "$ACR_LOGIN_SERVER/${APP_NAME}-frontend:${IMAGE_TAG}" \
    "$PROJECT_ROOT"
docker push "$ACR_LOGIN_SERVER/${APP_NAME}-frontend:${IMAGE_TAG}"

# ============================================================================
# Deploy Infrastructure
# ============================================================================

log "Deploying infrastructure with Bicep..."

ENABLE_BITGET="false"
if [[ -n "$BITGET_API_KEY" ]]; then
    ENABLE_BITGET="true"
fi

az deployment sub create \
    --location "$LOCATION" \
    --template-file "$SCRIPT_DIR/bicep/main.bicep" \
    --parameters \
        appName="$APP_NAME" \
        location="$LOCATION" \
        imageTag="$IMAGE_TAG" \
        acrName="$ACR_NAME" \
        llmProvider="${LLM_PROVIDER:-azure}" \
        azureOpenAIEndpoint="$AZURE_OPENAI_ENDPOINT" \
        azureOpenAIApiKey="$AZURE_OPENAI_API_KEY" \
        azureOpenAIDeployment="${AZURE_OPENAI_DEPLOYMENT:-gpt-4o}" \
        enableBitget="$ENABLE_BITGET" \
        bitgetApiKey="${BITGET_API_KEY:-}" \
        bitgetApiSecret="${BITGET_API_SECRET:-}" \
        bitgetPassphrase="${BITGET_PASSPHRASE:-}"

# ============================================================================
# Get Outputs
# ============================================================================

log ""
log "=========================================="
log "Deployment Complete!"
log "=========================================="
log ""

FRONTEND_URL=$(az containerapp show \
    --name "ca-${APP_NAME}-frontend" \
    --resource-group "$RG_NAME" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

BACKEND_URL=$(az containerapp show \
    --name "ca-${APP_NAME}-backend" \
    --resource-group "$RG_NAME" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "🚀 Application URLs:"
echo "   Frontend: https://$FRONTEND_URL"
echo "   Backend:  https://$BACKEND_URL"
echo ""
echo "📊 View logs:"
echo "   az containerapp logs show --name ca-${APP_NAME}-backend --resource-group $RG_NAME --follow"
echo ""
