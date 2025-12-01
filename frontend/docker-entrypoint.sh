#!/bin/sh
# Docker entrypoint script for frontend
# Injects runtime environment configuration before starting nginx

set -e

# Create runtime config from environment variables
# This allows API_URL to be configured at container runtime
cat > /usr/share/nginx/html/config.js << EOF
window.RUNTIME_CONFIG = {
  API_URL: "${API_URL:-http://localhost:8500}",
  WS_URL: "${WS_URL:-ws://localhost:8500}"
};
EOF

echo "Runtime config generated:"
cat /usr/share/nginx/html/config.js

# Execute the main command (nginx)
exec "$@"
