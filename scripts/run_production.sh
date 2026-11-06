#!/usr/bin/env bash
# ==============================================================================
# PikVaidya AI — Linux / POSIX Production Launcher
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================================================="
echo " PikVaidya AI — Unified Production Environment Launcher"
echo "================================================================="
echo "Project Root: ${PROJECT_ROOT}"

HOST="${1:-0.0.0.0}"
PORT="${2:-8000}"

# 1. Ensure uploads directory exists
UPLOAD_DIR="${PROJECT_ROOT}/uploads"
mkdir -p "${UPLOAD_DIR}"
echo "[1/4] Uploads storage directory verified: ${UPLOAD_DIR}"

# 2. Check and build frontend if needed
FRONTEND_DIST="${PROJECT_ROOT}/frontend/dist"
if [ ! -f "${FRONTEND_DIST}/index.html" ]; then
    echo "[2/4] Compiling React 18 production bundle..."
    cd "${PROJECT_ROOT}/frontend"
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm ci --prefer-offline || npm install
    fi
    npm run build
    cd "${PROJECT_ROOT}"
    echo "Frontend build completed successfully."
else
    echo "[2/4] Production frontend bundle found in frontend/dist."
fi

# 3. Configure Python Environment
echo "[3/4] Exporting environment variables..."
export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/backend"
export ENVIRONMENT="production"

# 4. Launch unified server
echo "[4/4] Starting Uvicorn on http://${HOST}:${PORT} ..."
echo "  - Web Dashboard:     http://localhost:${PORT}/"
echo "  - API Documentation: http://localhost:${PORT}/docs"
echo "  - Health Telemetry:  http://localhost:${PORT}/health"

exec python -m uvicorn app.main:app --host "${HOST}" --port "${PORT}" --app-dir "${PROJECT_ROOT}/backend"

