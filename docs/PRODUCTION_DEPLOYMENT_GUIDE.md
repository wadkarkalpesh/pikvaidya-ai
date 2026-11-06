# PikVaidya AI — Production Deployment & DevOps Runbook
**System Stage:** Step 8 Implementation  
**Status:** Production Ready  
**Targets:** Docker Compose / Bare-Metal Linux / Windows Server / Cloud Container Platforms  

---

## 1. Architectural Architecture & Topology

PikVaidya AI is packaged as an enterprise-grade, full-stack agricultural AI platform. It supports two main deployment topologies:

```
                            TOPOLOGY A: DOCKER COMPOSE CLUSTER
                            
        +-------------------------------------------------------------------------+
        |                          Docker Bridge Network                          |
        |                                                                         |
        |   +-------------------------------+   +-----------------------------+   |
        |   |   pikvaidya-api (Port 8000)   |   |  pikvaidya-postgres (5432)  |   |
        |   |   - React 18 SPA (dist/)      |   |  - PostgreSQL 16 Alpine     |   |
        |   |   - FastAPI Backend           |-->|  - Healthcheck pg_isready   |   |
        |   |   - Dual-Crop PyTorch Models  |   |  - Volume: pikvaidya_pgdata |   |
        |   |   - Volume: pikvaidya_uploads |   |                             |   |
        |   +-------------------------------+   +-----------------------------+   |
        +-------------------------------------------------------------------------+
                                        ^
                                        | (Nginx Reverse Proxy / SSL Termination)
                                     Internet / Farmers
```

```
                        TOPOLOGY B: UNIFIED BARE-METAL / STANDALONE
                        
        +-------------------------------------------------------------------------+
        |                           Host OS (Windows / Linux)                     |
        |                                                                         |
        |   +-----------------------------------------------------------------+   |
        |   |                       Unified FastAPI Process                   |   |
        |   |  - Static Mounts: / (index.html), /dashboard, /assets, /uploads |   |
        |   |  - API Endpoints: /api/v1/diagnose, /advisory, /weather, /chat   |   |
        |   |  - SQLite or Remote PostgreSQL Connection                       |   |
        |   +-----------------------------------------------------------------+   |
        +-------------------------------------------------------------------------+
```

---

## 2. Quick-Start Deployment Options

### Option A: Docker Compose (Recommended for Production)
The multi-stage `Dockerfile` compiles the Vite React frontend and builds a lightweight Python 3.11 image with CPU-optimized PyTorch:

```bash
# 1. Clone repository and navigate to root
cd "PikVaidya AI"

# 2. Configure production environment
cp .env.production.example .env

# 3. Build and launch services in background
docker compose up --build -d

# 4. Verify running services and healthchecks
docker compose ps
```
- **Web Dashboard:** `http://localhost:8000/`
- **Interactive OpenAPI Documentation:** `http://localhost:8000/docs`
- **Health Telemetry:** `http://localhost:8000/health`

---

### Option B: Bare-Metal / Native Server Run

If running on a bare-metal server without Docker:

#### On Windows (PowerShell):
```powershell
.\scripts\run_production.ps1 -Port 8000
```

#### On Linux / macOS (Bash):
```bash
chmod +x scripts/run_production.sh
./scripts/run_production.sh 0.0.0.0 8000
```

The launcher will automatically:
1. Verify the `uploads/` storage directory.
2. Compile the React 18 production bundle (`frontend/dist/`) via `npm run build` if missing.
3. Configure `PYTHONPATH` and production environment variables.
4. Launch Uvicorn with ASGI multi-worker serving.

---

## 3. Configuration & Environment Variables

All parameters are managed via environment variables (or `.env`):

| Variable | Description | Production Default |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime mode (`development`, `staging`, `production`) | `production` |
| `SECRET_KEY` | 32+ character cryptographic salt for JWT tokens | *Required securely generated string* |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+psycopg://user:pass@host:5432/db` |
| `CORS_ORIGINS` | JSON array of allowed frontend host origins | `["https://pikvaidya.yourdomain.com"]` |
| `UPLOAD_DIR` | Filesystem path for uploaded images and heatmaps | `/app/uploads` |
| `MAX_UPLOAD_SIZE_BYTES` | Maximum incoming image payload size | `10485760` (10MB) |
| `WEATHER_API_TIMEOUT`| Open-Meteo microclimate HTTP request timeout | `5.0` (seconds) |

---

## 4. Multi-Stage Dockerfile Internals

```dockerfile
# Stage 1: Node.js 20 Alpine compiles frontend SPA
FROM node:20-alpine AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --prefer-offline --no-audit
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 3.11 Slim production runtime
FROM python:3.11-slim AS production-runtime
RUN apt-get update && apt-get install -y --no-install-recommends curl libgomp1
WORKDIR /app
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY models/ /app/models/
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist
USER pikvaidya
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
```

### Highlights:
- **Zero Heavy CUDA Overhead:** PyTorch CPU wheels cut container size from ~8GB down to ~1.6GB.
- **Layer Caching:** Dependencies are installed prior to copying application code.
- **Security Hardening:** Runs as unprivileged `pikvaidya` non-root user.
- **Integrated Healthcheck:** Probes `/health` every 30 seconds with automatic container recovery.

---

## 5. Cloud Platform Deployment

### AWS ECS / Fargate
1. Build and push image to AWS ECR:
   ```bash
   aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker build -t pikvaidya-api .
   docker tag pikvaidya-api:latest <account>.dkr.ecr.<region>.amazonaws.com/pikvaidya-api:latest
   docker push <account>.dkr.ecr.<region>.amazonaws.com/pikvaidya-api:latest
   ```
2. Create an ECS Task Definition with 1 vCPU and 2GB RAM.
3. Attach an Application Load Balancer (ALB) terminating HTTPS/TLS.

### Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/<project-id>/pikvaidya-api
gcloud run deploy pikvaidya-api \
    --image gcr.io/<project-id>/pikvaidya-api \
    --platform managed \
    --region us-central1 \
    --memory 2Gi \
    --cpu 2 \
    --allow-unauthenticated
```

---

## 6. Backup, Recovery & Maintenance

### PostgreSQL Database Backups
```bash
# Automated daily dump
docker exec -t pikvaidya-postgres pg_dumpall -c -U pikvaidya_user > "backup_$(date +%Y%m%d).sql"

# Restoration
cat backup_20261106.sql | docker exec -i pikvaidya-postgres psql -U pikvaidya_user -d pikvaidya_db
```

### Uploads Storage Hygiene
Generated Grad-CAM heatmaps are written to `/app/uploads`. A daily cron job can purge files older than 30 days:
```bash
find /app/uploads -type f -mtime +30 -name "*_gradcam.jpg" -delete
```

---

## 7. Compliance & Statutory Safeguards

In accordance with the *Insecticides Act, 1968* and Central Insecticides Board & Registration Committee (CIBRC) regulations:
1. Chemical spray advice is only surfaced when confidence is calibrated ($T^*$) above the 70.0% threshold.
2. In moderate or ambiguous cases, chemical brand names are masked and agricultural university contact info is provided.
3. Every advisory payload requires personal protective equipment (PPE) notifications and Pre-Harvest Interval (PHI) warnings.

