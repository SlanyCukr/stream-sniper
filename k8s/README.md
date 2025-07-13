# Stream Sniper Kubernetes Deployment

This directory contains comprehensive Kubernetes deployment manifests for the Stream Sniper application, following cloud-native best practices for production-ready deployments.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Configurations](#environment-configurations)
- [Deployment Instructions](#deployment-instructions)
- [Configuration Management](#configuration-management)
- [Monitoring & Observability](#monitoring--observability)
- [Security](#security)
- [Scaling & Performance](#scaling--performance)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## 🏗️ Overview

The Stream Sniper Kubernetes deployment provides:

- **High Availability**: Multi-replica API deployment with auto-scaling
- **Microservices Architecture**: Separate API and collector services
- **Data Persistence**: PostgreSQL database with persistent storage
- **Caching Layer**: Redis for performance optimization
- **Security**: Network policies, RBAC, and secret management
- **Monitoring**: Prometheus metrics and health checks
- **Environment Management**: Kustomize overlays for dev/staging/prod

## 🔧 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingress       │    │   Load Balancer │    │   External DNS  │
│   Controller    │◄───┤                 │◄───┤                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  API Service    │    │  Redis Service  │    │ Postgres Service│
│  (3+ replicas)  │◄───┤  (1 replica)    │    │  (1 replica)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Pods      │    │   Redis Pod     │    │  Postgres Pod   │
│ - Health Checks │    │ - Persistent    │    │ - Persistent    │
│ - Auto Scaling  │    │   Storage       │    │   Storage       │
│ - Security      │    │ - Auth          │    │ - Backups       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Collector Jobs │
│ - Scheduled     │
│ - On-demand     │
│ - Data Pipeline │
└─────────────────┘
```

## 📋 Prerequisites

### Required Tools

```bash
# Kubernetes cluster access
kubectl version --client

# Kustomize (for environment management)
kustomize version

# Optional: Helm (for additional components)
helm version
```

### Cluster Requirements

- **Kubernetes Version**: 1.24+
- **Node Resources**: Minimum 4 CPU cores, 8GB RAM per node
- **Storage**: Dynamic volume provisioning or pre-configured PVs
- **Network**: CNI plugin with NetworkPolicy support
- **Ingress**: Nginx Ingress Controller or equivalent

### External Dependencies

- **Container Registry**: Access to pull Stream Sniper images
- **DNS**: Domain configuration for ingress
- **SSL Certificates**: cert-manager or manual certificate management
- **Monitoring**: Prometheus/Grafana (optional)

## 🚀 Quick Start

### 1. Clone and Navigate

```bash
cd /path/to/stream-sniper/k8s
```

### 2. Update Configuration

Edit the following files with your environment-specific values:

```bash
# Update domain names
vim ingress.yaml

# Update container registry
vim kustomization.yaml

# Update secrets (base64 encoded)
vim secrets.yaml
```

### 3. Deploy Base Configuration

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Deploy all components
kubectl apply -k .

# Or deploy specific environment
kubectl apply -k overlays/production/
```

### 4. Verify Deployment

```bash
# Check all resources
kubectl get all -n stream-sniper

# Check pod status
kubectl get pods -n stream-sniper -w

# Check ingress
kubectl get ingress -n stream-sniper
```

## 🌍 Environment Configurations

### Development Environment

```bash
# Deploy to development
kubectl apply -k overlays/development/

# Characteristics:
# - Single replica
# - Reduced resources
# - Debug logging
# - No rate limiting
# - Separate namespace: stream-sniper-dev
```

### Staging Environment

```bash
# Deploy to staging
kubectl apply -k overlays/staging/

# Characteristics:
# - 2 replicas
# - Moderate resources
# - Production-like configuration
# - Rate limiting enabled
# - Separate namespace: stream-sniper-staging
```

### Production Environment

```bash
# Deploy to production
kubectl apply -k overlays/production/

# Characteristics:
# - 5+ replicas
# - Full resources
# - Monitoring enabled
# - All security features
# - Namespace: stream-sniper
```

## 📖 Deployment Instructions

### Prerequisites Setup

1. **Container Images**

```bash
# Build and push your images
docker build -t your-registry.com/stream-sniper:v2.0.0 -f Dockerfile.api .
docker build -t your-registry.com/stream-sniper-collector:v2.0.0 -f Dockerfile.collector .
docker push your-registry.com/stream-sniper:v2.0.0
docker push your-registry.com/stream-sniper-collector:v2.0.0
```

2. **Update Image References**

```bash
# Update kustomization.yaml with your registry
sed -i 's|stream-sniper:2.0.0|your-registry.com/stream-sniper:v2.0.0|g' kustomization.yaml
```

### Step-by-Step Deployment

1. **Deploy Core Infrastructure**

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Deploy secrets and config
kubectl apply -f secrets.yaml
kubectl apply -f configmap.yaml

# Deploy storage
kubectl apply -f pvc.yaml
```

2. **Deploy Data Layer**

```bash
# Deploy PostgreSQL
kubectl apply -f postgres-deployment.yaml

# Deploy Redis
kubectl apply -f redis-deployment.yaml

# Wait for databases to be ready
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=postgres -n stream-sniper --timeout=300s
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=redis -n stream-sniper --timeout=300s
```

3. **Deploy Application Layer**

```bash
# Deploy services
kubectl apply -f services.yaml

# Deploy API
kubectl apply -f api-deployment.yaml

# Wait for API to be ready
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=stream-sniper-api -n stream-sniper --timeout=300s
```

4. **Deploy Network & Scaling**

```bash
# Deploy ingress
kubectl apply -f ingress.yaml

# Deploy autoscaling
kubectl apply -f hpa.yaml

# Deploy network policies
kubectl apply -f network-policies.yaml
```

5. **Deploy Data Collection**

```bash
# Deploy collector (update TWITCH_USERNAME first)
kubectl apply -f collector-deployment.yaml
```

### Health Verification

```bash
# Check deployment status
kubectl get deployments -n stream-sniper

# Check pod health
kubectl get pods -n stream-sniper

# Check services
kubectl get services -n stream-sniper

# Test API health
kubectl port-forward svc/stream-sniper-api-service 8080:80 -n stream-sniper &
curl http://localhost:8080/health

# Check logs
kubectl logs -f deployment/stream-sniper-api -n stream-sniper
```

## ⚙️ Configuration Management

### Environment Variables

Key configuration is managed through ConfigMaps and Secrets:

**ConfigMap (Non-sensitive)**:
- `LOG_LEVEL`: Application logging level
- `API_PORT`: API server port
- `POSTGRES_HOST`: Database hostname
- `REDIS_HOST`: Cache hostname
- `RATE_LIMIT_ENABLED`: Enable rate limiting

**Secrets (Sensitive)**:
- `POSTGRES_PASSWORD`: Database password
- `REDIS_PASSWORD`: Cache password
- `TWITCH_CLIENT_ID`: Twitch API credentials
- `TWITCH_CLIENT_SECRET`: Twitch API credentials

### Kustomize Structure

```
k8s/
├── base/                   # Base configuration
│   ├── *.yaml             # All base manifests
│   └── kustomization.yaml # Base kustomization
├── overlays/              # Environment-specific overlays
│   ├── development/       # Dev environment
│   ├── staging/           # Staging environment
│   └── production/        # Production environment
└── patches/               # Common patches
    ├── production-resources.yaml
    └── api-production-patch.yaml
```

### Updating Configuration

```bash
# Update ConfigMap
kubectl patch configmap stream-sniper-config -n stream-sniper --type merge -p '{"data":{"LOG_LEVEL":"DEBUG"}}'

# Update Secret (base64 encoded)
kubectl patch secret stream-sniper-secrets -n stream-sniper --type merge -p '{"data":{"NEW_KEY":"bmV3X3ZhbHVl"}}'

# Restart deployment to pick up changes
kubectl rollout restart deployment/stream-sniper-api -n stream-sniper
```

## 📊 Monitoring & Observability

### Health Checks

The application provides comprehensive health endpoints:

- **Liveness**: `/health` - Basic application health
- **Readiness**: `/health/ready` - Ready to serve traffic
- **Detailed**: `/health/detailed` - Comprehensive system status
- **Metrics**: `/metrics` - Prometheus metrics

### Prometheus Metrics

Available metrics include:

- `stream_sniper_component_health` - Component health status
- `stream_sniper_component_response_time_ms` - Response times
- `stream_sniper_system_cpu_percent` - CPU usage
- `stream_sniper_system_memory_percent` - Memory usage
- `http_requests_total` - HTTP request counters
- `http_request_duration_seconds` - Request latency

### Monitoring Setup

```bash
# Port-forward to access metrics
kubectl port-forward svc/stream-sniper-api-service 8080:8080 -n stream-sniper

# View metrics
curl http://localhost:8080/metrics

# View detailed health
curl http://localhost:8080/health/detailed
```

### Alerting Rules

The deployment includes PrometheusRule definitions for:

- API downtime alerts
- High error rate alerts
- Database connection failures
- Resource utilization alerts
- High latency alerts

## 🔒 Security

### Network Policies

The deployment includes comprehensive network policies:

- **Default Deny**: Block all traffic by default
- **API Access**: Allow ingress to API pods
- **Database Access**: Restrict database access to authorized pods
- **External Access**: Allow API to reach Twitch APIs
- **DNS Resolution**: Allow DNS queries

### RBAC Configuration

Service accounts with minimal required permissions:

- `stream-sniper-api`: API pods with monitoring access
- `stream-sniper-collector`: Collector pods with job management

### Security Contexts

All pods run with security contexts:

- Non-root user execution
- Read-only root filesystem (where possible)
- Dropped capabilities
- Security constraints

### Secrets Management

- All sensitive data in Kubernetes Secrets
- Base64 encoding for secret values
- Optional integration with external secret managers
- Automatic mounting into pods

### TLS/SSL Configuration

- Ingress TLS termination
- cert-manager integration ready
- Internal traffic encryption (optional)

## 📈 Scaling & Performance

### Horizontal Pod Autoscaler (HPA)

```yaml
# Scaling configuration
minReplicas: 3
maxReplicas: 10
targetCPUUtilizationPercentage: 70
targetMemoryUtilizationPercentage: 80
```

### Vertical Pod Autoscaler (VPA)

Optional VPA configuration for automatic resource optimization:

```bash
# Enable VPA (requires VPA controller)
kubectl apply -f hpa.yaml
```

### Pod Disruption Budget

Ensures availability during maintenance:

```yaml
minAvailable: 2  # Always keep 2 pods running
```

### Resource Requests and Limits

**Development**:
- Requests: 100m CPU, 128Mi memory
- Limits: 500m CPU, 512Mi memory

**Production**:
- Requests: 500m CPU, 512Mi memory
- Limits: 2000m CPU, 2Gi memory

### Performance Tuning

```bash
# Database connection pooling
DB_POOL_MIN_SIZE: "10"
DB_POOL_MAX_SIZE: "50"

# Redis caching
CACHE_TTL: "600"
CACHE_MAX_SIZE: "1000"

# Rate limiting
RATE_LIMIT_REQUESTS: "1000"
RATE_LIMIT_WINDOW: "60"
```

## 🔧 Troubleshooting

### Common Issues

1. **Pods Not Starting**

```bash
# Check pod status
kubectl describe pod <pod-name> -n stream-sniper

# Check logs
kubectl logs <pod-name> -n stream-sniper

# Check events
kubectl get events -n stream-sniper --sort-by='.lastTimestamp'
```

2. **Database Connection Issues**

```bash
# Test database connectivity
kubectl exec -it deployment/stream-sniper-api -n stream-sniper -- \
  psql -h postgres-service -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"

# Check database logs
kubectl logs deployment/postgres -n stream-sniper
```

3. **Redis Connection Issues**

```bash
# Test Redis connectivity
kubectl exec -it deployment/stream-sniper-api -n stream-sniper -- \
  redis-cli -h redis-service -a $REDIS_PASSWORD ping

# Check Redis logs
kubectl logs deployment/redis -n stream-sniper
```

4. **Ingress Not Working**

```bash
# Check ingress status
kubectl describe ingress stream-sniper-ingress -n stream-sniper

# Check ingress controller logs
kubectl logs -n ingress-nginx deployment/nginx-ingress-controller
```

### Debug Commands

```bash
# Get all resources
kubectl get all -n stream-sniper

# Describe failing pods
kubectl describe pods -l app.kubernetes.io/part-of=stream-sniper -n stream-sniper

# Check resource usage
kubectl top pods -n stream-sniper
kubectl top nodes

# Check persistent volumes
kubectl get pv,pvc -n stream-sniper

# Check secrets and configmaps
kubectl get secrets,configmaps -n stream-sniper
```

### Log Analysis

```bash
# Follow API logs
kubectl logs -f deployment/stream-sniper-api -n stream-sniper

# Get logs from all replicas
kubectl logs deployment/stream-sniper-api -n stream-sniper --all-containers=true

# Check specific time range
kubectl logs deployment/stream-sniper-api -n stream-sniper --since=1h

# Export logs for analysis
kubectl logs deployment/stream-sniper-api -n stream-sniper > api-logs.txt
```

## 🔧 Maintenance

### Updates and Rollouts

```bash
# Update image version
kubectl set image deployment/stream-sniper-api api=your-registry.com/stream-sniper:v2.1.0 -n stream-sniper

# Check rollout status
kubectl rollout status deployment/stream-sniper-api -n stream-sniper

# Rollback if needed
kubectl rollout undo deployment/stream-sniper-api -n stream-sniper

# View rollout history
kubectl rollout history deployment/stream-sniper-api -n stream-sniper
```

### Backup Procedures

```bash
# Database backup
kubectl exec deployment/postgres -n stream-sniper -- \
  pg_dump -U $POSTGRES_USER $POSTGRES_DB > stream-sniper-backup-$(date +%Y%m%d).sql

# Redis backup
kubectl exec deployment/redis -n stream-sniper -- \
  redis-cli -a $REDIS_PASSWORD BGSAVE
```

### Scaling Operations

```bash
# Manual scaling
kubectl scale deployment stream-sniper-api --replicas=5 -n stream-sniper

# Update HPA settings
kubectl patch hpa stream-sniper-api-hpa -n stream-sniper --type merge -p '{"spec":{"maxReplicas":15}}'
```

### Resource Cleanup

```bash
# Delete specific deployment
kubectl delete deployment stream-sniper-api -n stream-sniper

# Delete entire application
kubectl delete -k .

# Delete namespace (removes everything)
kubectl delete namespace stream-sniper
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [Stream Sniper Application Documentation](../CLAUDE.md)

## 🤝 Contributing

When updating Kubernetes manifests:

1. Validate YAML syntax
2. Test in development environment first
3. Update documentation
4. Follow security best practices
5. Update version tags and labels

---

**Note**: Replace placeholder values (domains, registry URLs, credentials) with your actual production values before deployment.