#!/bin/bash

# MagenticOne Showcase Setup Script
# This script sets up the complete environment for the MagenticOne showcase

set -e  # Exit on error

echo "🧲 MagenticOne Showcase - Setup Script"
echo "======================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    print_status "Checking for Docker..."
    if command -v docker &> /dev/null; then
        print_success "Docker is installed: $(docker --version)"
        return 0
    else
        print_error "Docker is not installed"
        echo "Please install Docker from: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
}

# Check if Docker Compose is installed
check_docker_compose() {
    print_status "Checking for Docker Compose..."
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose is installed: $(docker-compose --version)"
        return 0
    else
        print_error "Docker Compose is not installed"
        exit 1
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating directories..."
    mkdir -p outputs
    mkdir -p outputs/code_execution
    mkdir -p data
    print_success "Directories created"
}

# Copy environment file
setup_env() {
    print_status "Setting up environment configuration..."
    if [ ! -f .env ]; then
        cp config/.env.example .env
        print_success "Created .env file from template"
        print_warning "Please review and update .env file if needed"
    else
        print_warning ".env file already exists, skipping..."
    fi
}

# Start Docker services
start_services() {
    print_status "Starting Docker services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker services are running"
    else
        print_error "Failed to start Docker services"
        docker-compose logs
        exit 1
    fi
}

# Pull Ollama model
setup_ollama_model() {
    print_status "Checking Ollama setup..."
    print_warning "This project uses Ollama running on your host machine (not in Docker)"
    
    # Check if Ollama is available
    if command -v ollama &> /dev/null; then
        print_status "Ollama found on host machine"
        print_status "Checking if model is available..."
        
        # Try to pull the model (this will be quick if already present)
        if ollama pull gpt-oss:20b; then
            print_success "Ollama model ready"
        else
            print_warning "Failed to pull model. Make sure Ollama is running on your host."
            print_warning "You can manually run: ollama pull gpt-oss:20b"
        fi
    else
        print_warning "Ollama not found on host machine"
        print_warning "Please install Ollama from: https://ollama.ai"
        print_warning "Then run: ollama pull gpt-oss:20b"
    fi
}

# Test the setup
test_setup() {
    print_status "Testing the setup..."
    
    # Check if Ollama is responding
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        print_success "Ollama is responding"
    else
        print_warning "Ollama might not be fully ready yet, give it a few more seconds"
    fi
    
    # Check if containers are running
    if docker ps | grep -q "magentic"; then
        print_success "MagenticOne containers are running"
    else
        print_error "MagenticOne containers are not running"
    fi
}

# Display next steps
show_next_steps() {
    echo ""
    echo "======================================="
    echo "✅ Setup Complete!"
    echo "======================================="
    echo ""
    echo "🚀 You can now run the application:"
    echo ""
    echo "   # Interactive mode"
    echo "   docker exec -it magentic-app uv run python src/main.py"
    echo ""
    echo "   # Run an example"
    echo "   docker exec -it magentic-app uv run python examples/research_task.py"
    echo ""
    echo "   # Custom task"
    echo "   docker exec -it magentic-app uv run python src/main.py \"Your task here\""
    echo ""
    echo "📚 Documentation:"
    echo "   • README.md - Full documentation"
    echo "   • QUICKSTART.md - Quick reference guide"
    echo ""
    echo "🐛 Troubleshooting:"
    echo "   • Check logs: docker-compose logs -f"
    echo "   • Restart: docker-compose restart"
    echo "   • Stop: docker-compose down"
    echo ""
}

# Main setup process
main() {
    echo ""
    print_status "Starting setup process..."
    echo ""
    
    # Run all setup steps
    check_docker
    check_docker_compose
    create_directories
    setup_env
    start_services
    setup_ollama_model
    test_setup
    show_next_steps
}

# Run main function
main
