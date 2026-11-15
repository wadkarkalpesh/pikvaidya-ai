# 🐳 PikVaidya AI — Production Docker Deployment Guide

This guide details the single-command production deployment of **PikVaidya AI (पीकवैद्य AI)** using **Docker** and **Docker Compose**.

---

## 🏛️ Topology of the Containerized Stack

```
                  ┌──────────────────────────────────────────────┐
                  │          Host Port 8000 (HTTP / Web)         │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌─────────────────────────────────────────────────┐
                 │  Container: pikvaidya-api (Python 3.11 Slim)    │
                 │                                                 │
                 │  • Compiled React 19 Frontend SPA (Vite /dist)  │
                 │  • FastAPI ASGI Micro-Monolith (Uvicorn)        │
                 │  • PyTorch 2.x CPU Neural Inference Engines     │
                 │  • ONNX INT8 Offline WASM Assets Serving        │
                 │  • Trilingual Hybrid RAG Knowledge Engine       │
                 │  • Automated ReportLab PDF Generator            │
                 └──────────────┬──────────────────┬───────────────┘
                                │                  │
            Internal Database   │                  │  Persistent Volume
                 Connection     │                  │  /app/uploads
                                ▼                  ▼
┌──────────────────────────────────────────────┐  ┌───────────────────────┐
│ Container: pikvaidya-postgres (Postgres 16)  │  │ pikvaidya_uploads     │
│                                              │  └───────────────────────┘
│ • Relational Data: Users, Farms, Cycles,     │
│   Diagnoses, Expert Reviews, Audit Logs      │
│ • Persistent Volume: pikvaidya_pgdata        │
└──────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

1. **Docker Engine**: Version 24.0+ or Docker Desktop for Windows / macOS / Linux.
2. **Docker Compose**: Version v2.20+ or `docker-compose` v5+.
3. **RAM**: Minimum 4 GB recommended (for PyTorch CPU forward passes).
4. **Disk**: 5 GB free disk space.

---

## 🚀 Quickstart (One-Command Deployment)

### 1. Start the Complete Stack
From the project root, execute:
```bash
docker-compose up --build -d
```
*What happens:*
- **Stage 1**: A Node.js 20 Alpine container installs dependencies and compiles the React 19 frontend into optimized production bundles (`dist/`).
- **Stage 2**: A Python 3.11 Slim container installs CPU-optimized PyTorch and backend packages, bundles the models and agricultural knowledge base, and mounts the compiled frontend SPA.
- **Database**: PostgreSQL 16 Alpine container starts and configures the database with an active healthcheck.
- **Lifespan Startup**: The API waits for PostgreSQL to become healthy, automatically creates the 10 relational tables, and pre-loads the neural pathology networks.

---

### 2. Verify Container Health
Check that both containers are running and reported as healthy:
```bash
docker-compose ps
```

Expected output:
```text
NAME                 IMAGE                  COMMAND                  SERVICE    STATUS
pikvaidya-postgres   postgres:16-alpine     "docker-entrypoint.s…"   postgres   Up (healthy)
pikvaidya-api        pikvaidya-ai-api       "python -m uvicorn a…"   api        Up (healthy)
```

---

### 3. Access the Services

| Interface | URL | Purpose |
| :--- | :--- | :--- |
| **PikVaidya Web App** | `http://localhost:8000/` | Full responsive UI in Marathi, Hindi, and English |
| **Interactive Swagger API** | `http://localhost:8000/docs` | OpenAPI documentation for all 55 endpoints |
| **System Health Check** | `http://localhost:8000/health` | Service uptime and heartbeat |
| **PostgreSQL Port** | `localhost:5432` | Exposed for database administration (pgAdmin / DBeaver) |

---

## 🛠️ Management & Operations Commands

### View Live Logs
```bash
# Stream all logs
docker-compose logs -f

# Stream only backend/frontend application logs
docker-compose logs -f api

# Stream database logs
docker-compose logs -f postgres
```

### Run Database Migrations (Alembic)
To upgrade schema versions or run custom migrations inside the container:
```bash
docker-compose exec api alembic -c backend/alembic.ini upgrade head
```

### Access Container Shell
```bash
# Enter the application container
docker-compose exec api /bin/bash

# Connect directly to PostgreSQL via psql
docker-compose exec postgres psql -U pikvaidya_user -d pikvaidya_db
```

### Stop the Containers
```bash
# Stop containers without deleting data
docker-compose down

# Stop containers AND wipe all database & upload volumes (clean reset)
docker-compose down -v
```

---

## 🔐 Environment Configuration

Environment variables can be overridden in `docker-compose.yml` or via a `.env` file:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Deployment mode (`production` / `staging`) |
| `PROJECT_NAME` | `PikVaidya AI` | Application title |
| `DATABASE_URL` | `postgresql+psycopg://...` | Connection URI to the Postgres container |
| `SECRET_KEY` | *(32+ characters)* | JWT HMAC signature encryption key |
| `CORS_ORIGINS` | `["http://localhost:8000", ...]` | Allowed client domains |
| `UPLOAD_DIR` | `/app/uploads` | Path for saving uploaded leaf scans |
| `LOG_LEVEL` | `INFO` | Console log verbosity |

---

## 🛡️ Production Hardening Checklist

1. **Non-Root Execution**: The API container executes as a dedicated unprivileged system user (`pikvaidya:pikvaidya`), preventing root escalation attacks.
2. **Persistent Volumes**: `pikvaidya_pgdata` ensures all farmer records, diagnostics, and audit logs persist across container restarts.
3. **Layer Caching**: `frontend/package.json` and `backend/requirements.txt` are cached in Docker layers to ensure sub-minute rebuilds when only code changes.
4. **Lightweight Image**: Multi-stage compilation discards heavy Node.js build tools and build caches, delivering a clean runtime image.
