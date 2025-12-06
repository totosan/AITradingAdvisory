# Frontend Dockerfile for AgenticTrades Web UI
# Multi-stage build: Node for build, nginx for serving

# ============================================================================
# Stage 1: Build
# ============================================================================
FROM node:20-alpine AS builder

WORKDIR /build

# Copy package files first (cache layer)
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy source files
COPY frontend/ ./

# Build production bundle
RUN npm run build

# ============================================================================
# Stage 2: Production (nginx)
# ============================================================================
FROM nginx:alpine AS production

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/nginx.conf

# Copy built assets from builder stage
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy entrypoint script for runtime config
COPY frontend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create non-root user for nginx
RUN adduser -D -H -u 1000 -s /sbin/nologin nginx-user \
    && chown -R nginx-user:nginx-user /usr/share/nginx/html \
    && chown -R nginx-user:nginx-user /var/cache/nginx \
    && chown -R nginx-user:nginx-user /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx-user:nginx-user /var/run/nginx.pid

# Environment variables for runtime configuration
ENV API_URL=http://backend:8500 \
    WS_URL=ws://backend:8500

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/health || exit 1

# Use entrypoint to inject runtime config
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
