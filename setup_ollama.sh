#!/bin/bash

# Script to pull and set up the Ollama model
# This should be run after docker-compose up

echo "Setting up Ollama model..."

# Wait for Ollama to be ready
echo "Waiting for Ollama service..."
sleep 10

# Pull the model (using a smaller model that works well on Mac)
# deepseek-r1:1.5b is a good alternative if gpt-oss:20b is not available
docker exec magentic-ollama ollama pull deepseek-r1:1.5b

echo "Model setup complete!"
echo "You can now run the AgenticTrades application."
