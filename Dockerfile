# ==============================================================================
# PikVaidya AI — Enterprise Multi-Stage Production Dockerfile
# ==============================================================================
# Architecture:
#   Stage 1 (Frontend Builder): Node.js 20 Alpine compiles React 18 + Vite SPA
#   Stage 2 (Production Runtime): Python 3.11 Slim with CPU-optimized PyTorch
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Frontend SPA Compilation
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

# Leverage Docker layer caching for node dependencies
COPY frontend/package*.json ./
RUN npm ci --prefer-offline --no-audit

# Copy frontend source files and compile production bundle
COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Python Runtime & Unified Serving
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS production-runtime

# System dependencies: curl for healthcheck, libgomp for OpenMP/PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install CPU-optimized PyTorch first
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY backend/requirements.txt ./backend_requirements.txt
RUN pip install --no-cache-dir -r backend_requirements.txt

# Copy backend codebase
COPY backend/ /app/backend/

# Copy model artifacts
COPY models/ /app/models/

# Copy compiled frontend SPA from Stage 1
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# Create uploads directory and runtime directories
RUN mkdir -p /app/uploads /app/data && chmod -R 777 /app/uploads /app/data

# Security: Create non-root system user
RUN groupadd -r pikvaidya && useradd -r -g pikvaidya -d /app -s /sbin/nologin pikvaidya && \
    chown -R pikvaidya:pikvaidya /app

USER pikvaidya

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend:/app \
    PORT=8000 \
    HOST=0.0.0.0

# Expose primary application port
EXPOSE 8000

# Docker healthcheck against FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Production server execution entrypoint
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]

