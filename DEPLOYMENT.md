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
- React application built with production optimizations
- Nginx-based container serving static files and proxying API requests
- HTTPS via reverse proxy at `stream-sniper.slanycukr.com`
- Internal API proxy at `/api/*` routes to backend

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
- PostgreSQL 16 with persistent volume storage
- Automatic schema initialization
- Health checks and backup considerations

## Monitoring

### Health Checks

- **Frontend**: `curl -f https://stream-sniper.slanycukr.com`
- **API**: `curl -f https://stream-sniper.slanycukr.com/api/health`
- **Database**: `docker-compose exec postgres pg_isready`

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
3. **Database connection**: Verify PostgreSQL container is running
4. **Port conflicts**: Check autossh tunnels are active
5. **Permission errors**: Ensure GitHub Actions runner has proper permissions

### Recovery

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Clean up containers and volumes (⚠️ destroys data)
docker-compose -f docker-compose.prod.yml down -v
docker system prune -f

# Redeploy
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## Security Considerations

- All secrets are in `.env.prod` (not committed to git)
- SSL certificates automatically renewed by Let's Encrypt
- Database password is secure and not default
- JWT secret key is cryptographically secure
- CORS configured for production domains only
- Nginx security headers enabled

## Backup Strategy

### Database Backup

```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U stream_sniper_user stream_sniper > backup.sql

# Restore backup
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U stream_sniper_user stream_sniper < backup.sql
```

### Application Data

- Docker volumes are persistent (`postgres_data`)
- Regular system backups of RPI storage recommended
- Configuration files backed up in git repository

## Performance Optimization

- Frontend: Static file serving with nginx caching
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