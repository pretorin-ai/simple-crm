# Docker Deployment

Pretorin CRM ships with Docker Compose for production-like deployment.

## Prerequisites

- Docker Engine 20+
- Docker Compose v2+

## Quick Deploy

```bash
git clone https://github.com/pretorin/simple-crm.git
cd simple-crm

# Configure environment variables in docker-compose.yml or use .env
# At minimum, change SECRET_KEY and database credentials

docker compose up -d
```

The services start on:

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3000 | `http://localhost:3000` |
| Backend | 8000 | `http://localhost:8000` |
| PostgreSQL | 5432 | Internal only |

## Services

### PostgreSQL (db)

- Image: `postgres:16-alpine`
- Default credentials: user `crm`, password `crm`, database `crm`
- Data persisted in a Docker volume (`pgdata`)
- Health check runs every 5 seconds

### Backend

- Built from `backend/Dockerfile` (Python 3.12-slim, non-root user)
- Runs Alembic migrations automatically before starting uvicorn (via `entrypoint.sh`)
- Depends on PostgreSQL (waits for health check)
- Resource limits: 1 CPU, 1GB memory; reservations: 0.5 CPU, 512MB
- Graceful shutdown: 30-second timeout for in-flight requests (`stop_grace_period: 35s`)
- JSON logging driver with rotation (10MB max, 3 files)
- Environment variables configured in `docker-compose.yml`

### Frontend

- Built from `frontend/Dockerfile` (multi-stage: Node build, then Nginx serve)
- Depends on backend (waits for health check)
- Nginx serves the built React app and proxies API requests

## Configuration

Edit the `docker-compose.yml` environment section or use a `.env` file:

```yaml
environment:
  - DATABASE_URL=postgresql://crm:crm@db:5432/crm
  - SECRET_KEY=your-production-secret-key
  - ENV=production
  - FRONTEND_URL=https://your-domain.com
  - GOOGLE_CLIENT_ID=your-client-id
  - GOOGLE_CLIENT_SECRET=your-client-secret
```

## Updating

```bash
git pull
docker compose build
docker compose up -d
```

## Data Persistence & Backups

PostgreSQL data is stored in the `pgdata` Docker volume.

### Using the backup script (recommended)

```bash
# Run a one-off backup
./scripts/backup.sh

# Install a nightly cron job (2 AM)
./scripts/backup.sh --install-cron

# Backup to a custom directory
./scripts/backup.sh /path/to/backups
```

Backups are compressed with gzip and old backups are pruned automatically (default: 30 days retention).

### Manual backup/restore

```bash
# Backup
docker compose exec db pg_dump -U crm --clean --if-exists --no-owner crm > backup.sql

# Restore
docker compose exec -T db psql -U crm crm < backup.sql
```

## Troubleshooting

### Backend won't start

Check logs:

```bash
docker compose logs backend
```

Common issues:
- `SECRET_KEY` not set
- Database connection refused (PostgreSQL not ready yet -- Docker Compose should handle this with health checks)

### Frontend returns 502

The backend may not be healthy yet. Check:

```bash
docker compose ps
docker compose logs backend
```
