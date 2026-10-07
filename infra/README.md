# PikVaidya AI - Infrastructure & Deployment

This directory contains infrastructure-as-code and containerization files for running PikVaidya AI services.

## Services
- `docker-compose.yml`: Launches a production-grade PostgreSQL 16 database with healthchecks and persistent storage volumes.

## Starting Infrastructure
```bash
# Start PostgreSQL in the background
docker-compose up -d

# Check status
docker-compose ps

# Stop services
docker-compose down
```
