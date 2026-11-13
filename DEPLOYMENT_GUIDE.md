# PikVaidya AI — Complete Production Deployment & Operations Guide

**Document Version:** 2.0  
**Target Environments:** Ubuntu 22.04 / 24.04 LTS, Debian 12, or Enterprise Container Runtimes (Docker / Kubernetes)  
**Security Standard:** HTTPS (TLS 1.3), Non-root execution, Least privilege  

---

## 1. Hardware & System Prerequisites

| Resource | Minimum Requirement (Staging / Small Pilot) | Recommended (Production Cluster) |
| :--- | :--- | :--- |
| **CPU Architecture** | 4 Cores (x86_64 or ARM64) | 8–16 Cores (AVX2 / NEON instruction support) |
| **System Memory (RAM)** | 8 GB | 16–32 GB ECC RAM |
| **Storage (Disk)** | 50 GB NVMe SSD | 250+ GB NVMe SSD (Encrypted at rest) |
| **GPU Acceleration** | None (CPU inference via INT8 ONNX) | NVIDIA T4 / A10G (Optional for large batch retraining) |
| **Operating System** | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS Server |
| **Python Runtime** | Python 3.11 – 3.13 | Python 3.13 with `uv` package manager |
| **Relational Database** | SQLite (Single-node / Edge) | PostgreSQL 15+ with Connection Pooling |

---

## 2. Production Environment Variables (`.env.production`)

Create `.env.production` in the project root:

```bash
# Core Environment
ENVIRONMENT=production
DEBUG=false
PROJECT_NAME="PikVaidya AI Enterprise"
VERSION="2.0.0"

# Cryptographic Secret (MUST be at least 32 characters, cryptographically random)
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY="c8f1e9a4d2b7e6f3a8b5c9d1e2f4a7b9c1d3e5f7a9b2c4d6e8f0a2b4c6d8e0f2"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Configuration (PostgreSQL 15+)
DATABASE_URL=postgresql+psycopg2://pikvaidya_user:SecureFarmDbPass2026@127.0.0.1:5432/pikvaidya_prod

# CORS Allowed Origins
CORS_ORIGINS=["https://pikvaidya.in","https://app.pikvaidya.in","https://api.pikvaidya.in"]

# Storage & Uploads
UPLOAD_DIR=/var/pikvaidya/uploads
MAX_UPLOAD_SIZE_BYTES=10485760

# Model Paths
MODEL_DIR=/var/pikvaidya/models
SUGARCANE_MODEL_PATH=/var/pikvaidya/models/sugarcane_model.pth
TOMATO_MODEL_PATH=/var/pikvaidya/models/tomato_model.pth
ONION_MODEL_PATH=/var/pikvaidya/models/onion_model.pth
CROP_DETECTOR_PATH=/var/pikvaidya/models/crop_detector.pth

# External Microclimate APIs
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1/forecast
WEATHER_CACHE_TTL_SECONDS=1800
```

---

## 3. Containerized Deployment via Docker & Docker Compose

### 3.1 Production Backend Dockerfile (`backend/Dockerfile`)
```dockerfile
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ENVIRONMENT=production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application and model artifacts
COPY backend/app /app/app
COPY models /app/models
COPY datasets /app/datasets

# Create non-root system user
RUN useradd -m -u 1001 pikvaidya && \
    mkdir -p /app/uploads && \
    chown -R pikvaidya:pikvaidya /app

USER pikvaidya

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
```

### 3.2 Production Docker Compose (`docker-compose.prod.yml`)
```yaml
version: "3.9"

services:
  db:
    image: postgres:15-alpine
    container_name: pikvaidya_db
    restart: always
    environment:
      POSTGRES_DB: pikvaidya_prod
      POSTGRES_USER: pikvaidya_user
      POSTGRES_PASSWORD: SecureFarmDbPass2026
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pikvaidya_user -d pikvaidya_prod"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: pikvaidya_backend
    restart: always
    env_file: .env.production
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - uploads_data:/app/uploads
      - ./models:/app/models:ro
    ports:
      - "127.0.0.1:8000:8000"

  frontend:
    image: nginx:alpine
    container_name: pikvaidya_frontend
    restart: always
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "80:80"
      - "443:443"

volumes:
  postgres_data:
  uploads_data:
```

---

## 4. Systemd Native Linux Service Deployment

For bare-metal Ubuntu servers running Uvicorn directly under a systemd daemon:

`/etc/systemd/system/pikvaidya.service`:
```ini
[Unit]
Description=PikVaidya AI FastAPI Backend Application
After=network.target postgresql.service

[Service]
Type=simple
User=pikvaidya
Group=pikvaidya
WorkingDirectory=/var/www/pikvaidya
EnvironmentFile=/var/www/pikvaidya/.env.production
ExecStart=/var/www/pikvaidya/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/pikvaidya/access.log \
    --error-logfile /var/log/pikvaidya/error.log \
    --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pikvaidya
sudo systemctl start pikvaidya
sudo systemctl status pikvaidya
```

---

## 5. Nginx Reverse Proxy & TLS Configuration

`/etc/nginx/sites-available/pikvaidya.in`:
```nginx
server {
    listen 80;
    server_name api.pikvaidya.in app.pikvaidya.in;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.pikvaidya.in;

    ssl_certificate /etc/letsencrypt/live/api.pikvaidya.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.pikvaidya.in/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 12M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }

    location /uploads/ {
        alias /var/pikvaidya/uploads/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```

---

## 6. Database Migrations & Health Monitoring

### 6.1 Executing Database Migrations
```bash
# Run schema upgrades to latest migration head
alembic upgrade head
```

### 6.2 Health Probes & Monitoring
- **Liveness Probe:** `GET /health` (Returns HTTP 200 OK)
- **Readiness Probe:** `GET /api/v1/health` (Verifies DB connection and versioned API layer)
- **Deep Telemetry Probe:** `GET /api/v1/admin/telemetry` (Requires Admin Bearer token; reports process memory, CPU utilization, and loaded model weights)

### 6.3 Automated Database Backup Script (`scripts/backup_db.sh`)
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/pikvaidya"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Perform PostgreSQL binary dump
pg_dump -U pikvaidya_user -h 127.0.0.1 -Fc pikvaidya_prod > "$BACKUP_DIR/db_$TIMESTAMP.dump"

# Retain only last 14 days of backups
find "$BACKUP_DIR" -type f -name "*.dump" -mtime +14 -delete
```
