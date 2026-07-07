# Stream Sniper - Deployment Guide

## Overview

Stream Sniper uses automated GitHub Actions deployment to the RPI infrastructure. When code is pushed to the `main` branch, it automatically deploys to the production environment.

## Infrastructure

- **RPI5 8GB (pi5ram8)**: Main deployment target
- **VPS**: Nginx reverse proxy with SSL termination
- **Domains**: 
  - Frontend: `https://stream-sniper.slanycukr.com`
  - API: `https://stream-sniper.slanycukr.com/api` (proxied through frontend)

## Prerequisites

### 1. Self-Hosted GitHub Actions Runner

The RPI5 8GB must have a self-hosted GitHub Actions runner installed and configured:

```bash
# On RPI5 8GB
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-arm64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-arm64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-arm64-2.311.0.tar.gz
./config.sh --url https://github.com/slanycukr/stream-sniper --token YOUR_TOKEN
sudo ./svc.sh install
sudo ./svc.sh start
```

### 2. Production Environment Configuration

Create `.env.prod` file on the RPI with production secrets:

```bash
# On RPI5 8GB at /home/pi/stream-sniper/.env.prod
cp .env.prod.template .env.prod
# Edit .env.prod with real production values
```

**Required secrets to update:**
- `POSTGRES_PASSWORD`: Secure database password
- `SECRET_KEY`: Long random string for JWT signing
- `TWITCH_CLIENT_ID`: Twitch application client ID
- `TWITCH_CLIENT_SECRET`: Twitch application client secret

### 3. Port Configuration

Ensure autossh tunnel is configured for the frontend:
- Port 3001: Frontend (includes API proxy)

Current autossh configuration in `/etc/default/autossh`:
```bash
SSH_OPTIONS="-N -R 3001:localhost:3001 ..."
```

### 4. DNS Configuration

Add DNS A record pointing to VPS IP (89.221.212.146):
- `stream-sniper.slanycukr.com`

### 5. SSL Certificates

SSL certificates are automatically managed by Let's Encrypt via certbot on the VPS.

## Deployment Process

### Automatic Deployment

1. **Push to main branch** triggers GitHub Actions
2. **Self-hosted runner** on RPI executes deployment workflow
3. **Code update** via `git pull` on RPI
4. **Docker images** are built locally on RPI
5. **Services deployed** via docker-compose
6. **Health checks** verify successful deployment

### Manual Deployment

If needed, you can deploy manually:

```bash
# SSH to RPI5 8GB
ssh -p 2222 pi@89.221.212.146

# Navigate to project directory
cd /home/pi/stream-sniper

# Pull latest code
git pull origin main

# Deploy with production configuration
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Verify deployment
docker-compose -f docker-compose.prod.yml ps
curl -f http://localhost:3001
curl -f http://localhost:5002/health
```

## Services

### Frontend (Port 3001)
- Next.js app built with `output: standalone` — a **Node server** runs in the
  container (`node server.js`), not nginx. Prod compose maps host `3001 -> 3000`.
- HTTPS via VPS reverse proxy at `stream-sniper.slanycukr.com`
- Internal API proxy: Next.js `rewrites()` forward `/api/*` to the backend
  (`API_PROXY_TARGET=http://stream-sniper-api:5002`)

### Backend API (Internal)
- FastAPI application with authentication and admin features
- PostgreSQL database integration
- Accessible via frontend proxy at `stream-sniper.slanycukr.com/api`
- Not exposed externally (internal Docker network only)

### Tracking Service
- Background service for automated streamer monitoring
- Processes stream chat data when streams end
- Shares database with API service

### Database
- PostgreSQL runs **on the RPI host**, not in Docker Compose. Containers reach it
  via the Docker bridge gateway (`POSTGRES_HOST=172.17.0.1`).
- Schema is applied **manually** (`create_table.sql`) — no automatic init and no
  `postgres_data` Docker volume.

## Monitoring

### Health Checks

- **Frontend**: `curl -f https://stream-sniper.slanycukr.com`
- **API**: `curl -f https://stream-sniper.slanycukr.com/api/health`
- **Database** (host Postgres): `pg_isready -h localhost -p 5432`

### Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs

# Specific service
docker-compose -f docker-compose.prod.yml logs stream-sniper-api

# Follow logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Container Status

```bash
docker-compose -f docker-compose.prod.yml ps
```

## Troubleshooting

### Common Issues

1. **Deployment fails**: Check `.env.prod` exists and has correct values
2. **SSL certificate errors**: Ensure DNS records point to VPS IP
3. **Database connection**: Verify the host PostgreSQL is running (`pg_isready -h localhost`)
4. **Port conflicts**: Check autossh tunnels are active
5. **Permission errors**: Ensure GitHub Actions runner has proper permissions

### Recovery

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down --remove-orphans

# Clean up dangling images only (this RPI is shared — do NOT run
# `docker system prune --volumes`, which can wipe other projects' data).
# The database lives on the host, so no Docker volumes hold app data.
docker image prune -f

# Redeploy
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## Security Considerations

- All secrets are in `.env.prod` (not committed to git). The API/tracking
  containers **fail to start** without a JWT signing secret (`SECRET_KEY`).
- SSL certificates automatically renewed by Let's Encrypt (on the VPS)
- Database password must be set to a strong, non-default value in `.env.prod`
- JWT secret key must be a long random string in `.env.prod`
- Note: `docker-compose.prod.yml` currently sets `CORS_ORIGINS=["*"]`. Tighten to
  the production domain (`.env.prod.template` shows the intended value).

## Backup Strategy

### Database Backup

PostgreSQL runs on the RPI **host**, not in a container — back it up with the
host `pg_dump`/`psql` directly (there is no `postgres` compose service):

```bash
# Create backup (run on the RPI host)
pg_dump -h localhost -p 5432 -U stream_sniper_user stream_sniper > backup.sql

# Restore backup
psql -h localhost -p 5432 -U stream_sniper_user stream_sniper < backup.sql
```

### Application Data

- Database data lives in the host Postgres data directory (no Docker volume)
- Regular system backups of RPI storage recommended
- Configuration files backed up in git repository

## Performance Optimization

- Frontend: Next.js standalone Node server (automatic static/prerender optimization)
- Backend: FastAPI with async/await patterns
- Database: PostgreSQL with proper indexing
- Infrastructure: Local deployment reduces latency
- Monitoring: Health checks and prometheus metrics available

## Updates

The system automatically updates when code is pushed to main branch. For major updates:

1. Test changes in development environment
2. Update documentation if needed
3. Push to main branch
4. Monitor deployment logs
5. Verify all services are healthy