# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy uv from the official Docker image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .python-version README.md ./
COPY src/ ./src/
COPY config/ ./config/
COPY examples/ ./examples/

# Install dependencies
RUN uv pip install --system -e .

# Create outputs directory with subdirectories
RUN mkdir -p /app/outputs/code_execution/outputs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:/app

EXPOSE 8000

# Default command
CMD ["uv", "run", "python", "src/main.py"]
