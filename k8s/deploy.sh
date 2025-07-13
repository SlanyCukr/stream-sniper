#!/bin/bash

# Stream Sniper Kubernetes Deployment Script
# This script automates the deployment of Stream Sniper to Kubernetes

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEFAULT_NAMESPACE="stream-sniper"
DEFAULT_ENVIRONMENT="development"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Stream Sniper Kubernetes Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    deploy      Deploy Stream Sniper to Kubernetes
    destroy     Remove Stream Sniper from Kubernetes
    status      Show deployment status
    logs        Show application logs
    shell       Open shell in API pod
    validate    Validate Kubernetes manifests
    backup      Backup database
    restore     Restore database from backup

Options:
    -e, --environment ENV    Target environment (development, staging, production)
    -n, --namespace NS       Kubernetes namespace (default: stream-sniper)
    -i, --image IMAGE        Container image tag (default: latest)
    -r, --registry REGISTRY  Container registry URL
    -d, --dry-run           Show what would be done without executing
    -v, --verbose           Verbose output
    -h, --help              Show this help message

Examples:
    $0 deploy -e development
    $0 deploy -e production -i v2.0.0 -r your-registry.com
    $0 destroy -e staging
    $0 status -n stream-sniper-dev
    $0 logs -n stream-sniper
    $0 backup
    $0 validate

Environment Variables:
    KUBECONFIG              Path to kubeconfig file
    CONTAINER_REGISTRY      Default container registry
    IMAGE_TAG              Default image tag
    TWITCH_USERNAME        Default Twitch username for collector
EOF
}

# Prerequisites check
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required but not installed"
        exit 1
    fi
    
    # Check kustomize
    if ! command -v kustomize &> /dev/null; then
        log_warning "kustomize not found, using kubectl kustomize"
    fi
    
    # Check cluster access
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    # Check if we have access to the namespace
    if kubectl get namespace "$namespace" &> /dev/null; then
        log_info "Namespace '$namespace' exists"
    else
        log_warning "Namespace '$namespace' does not exist - will be created"
    fi
    
    log_success "Prerequisites check passed"
}

# Validate Kubernetes manifests
validate_manifests() {
    log_info "Validating Kubernetes manifests..."
    
    cd "$SCRIPT_DIR"
    
    # Validate base manifests
    for file in *.yaml; do
        if [[ -f "$file" ]]; then
            if kubectl apply --dry-run=client -f "$file" &> /dev/null; then
                log_info "✅ $file: Valid"
            else
                log_error "❌ $file: Invalid"
                return 1
            fi
        fi
    done
    
    # Validate environment-specific manifests
    if [[ -d "overlays/$environment" ]]; then
        if kubectl apply --dry-run=client -k "overlays/$environment" &> /dev/null; then
            log_info "✅ overlays/$environment: Valid"
        else
            log_error "❌ overlays/$environment: Invalid"
            return 1
        fi
    fi
    
    log_success "All manifests are valid"
}

# Deploy Stream Sniper
deploy() {
    log_info "Deploying Stream Sniper to Kubernetes..."
    log_info "Environment: $environment"
    log_info "Namespace: $namespace"
    log_info "Image: $image_tag"
    
    cd "$SCRIPT_DIR"
    
    # Create namespace if it doesn't exist
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy based on environment
    if [[ -d "overlays/$environment" ]]; then
        log_info "Deploying environment-specific configuration..."
        if [[ "$dry_run" == "true" ]]; then
            kubectl apply --dry-run=client -k "overlays/$environment"
        else
            kubectl apply -k "overlays/$environment"
        fi
    else
        log_info "Deploying base configuration..."
        if [[ "$dry_run" == "true" ]]; then
            kubectl apply --dry-run=client -k .
        else
            kubectl apply -k .
        fi
    fi
    
    if [[ "$dry_run" == "false" ]]; then
        # Wait for deployments to be ready
        log_info "Waiting for deployments to be ready..."
        
        # Wait for PostgreSQL
        kubectl wait --for=condition=Available deployment/postgres -n "$namespace" --timeout=300s || true
        
        # Wait for Redis
        kubectl wait --for=condition=Available deployment/redis -n "$namespace" --timeout=300s || true
        
        # Wait for API
        kubectl wait --for=condition=Available deployment/stream-sniper-api -n "$namespace" --timeout=300s || true
        
        # Check deployment status
        kubectl get deployments -n "$namespace"
        kubectl get services -n "$namespace"
        kubectl get ingress -n "$namespace"
        
        log_success "Stream Sniper deployed successfully!"
        
        # Show access information
        show_access_info
    else
        log_info "Dry run completed - no changes made"
    fi
}

# Destroy Stream Sniper deployment
destroy() {
    log_warning "This will remove Stream Sniper from Kubernetes"
    log_warning "Environment: $environment"
    log_warning "Namespace: $namespace"
    
    if [[ "$dry_run" == "false" ]]; then
        read -p "Are you sure you want to continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Operation cancelled"
            exit 0
        fi
    fi
    
    cd "$SCRIPT_DIR"
    
    # Delete based on environment
    if [[ -d "overlays/$environment" ]]; then
        log_info "Removing environment-specific configuration..."
        if [[ "$dry_run" == "true" ]]; then
            kubectl delete --dry-run=client -k "overlays/$environment"
        else
            kubectl delete -k "overlays/$environment" || true
        fi
    else
        log_info "Removing base configuration..."
        if [[ "$dry_run" == "true" ]]; then
            kubectl delete --dry-run=client -k .
        else
            kubectl delete -k . || true
        fi
    fi
    
    if [[ "$dry_run" == "false" ]]; then
        # Optionally remove namespace
        read -p "Remove namespace '$namespace'? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kubectl delete namespace "$namespace" || true
            log_success "Namespace '$namespace' removed"
        fi
        
        log_success "Stream Sniper removed successfully!"
    else
        log_info "Dry run completed - no changes made"
    fi
}

# Show deployment status
show_status() {
    log_info "Stream Sniper deployment status:"
    log_info "Namespace: $namespace"
    
    echo
    echo "=== Deployments ==="
    kubectl get deployments -n "$namespace" -o wide || true
    
    echo
    echo "=== Pods ==="
    kubectl get pods -n "$namespace" -o wide || true
    
    echo
    echo "=== Services ==="
    kubectl get services -n "$namespace" -o wide || true
    
    echo
    echo "=== Ingress ==="
    kubectl get ingress -n "$namespace" -o wide || true
    
    echo
    echo "=== Persistent Volume Claims ==="
    kubectl get pvc -n "$namespace" -o wide || true
    
    echo
    echo "=== HPA ==="
    kubectl get hpa -n "$namespace" -o wide || true
    
    # Show recent events
    echo
    echo "=== Recent Events ==="
    kubectl get events -n "$namespace" --sort-by='.lastTimestamp' | tail -10 || true
}

# Show application logs
show_logs() {
    log_info "Stream Sniper application logs:"
    log_info "Namespace: $namespace"
    
    # Get API logs
    echo "=== API Logs ==="
    kubectl logs -n "$namespace" deployment/stream-sniper-api --tail=50 || true
    
    echo
    echo "=== Database Logs ==="
    kubectl logs -n "$namespace" deployment/postgres --tail=20 || true
    
    echo
    echo "=== Redis Logs ==="
    kubectl logs -n "$namespace" deployment/redis --tail=20 || true
    
    # Show recent collector jobs
    echo
    echo "=== Recent Collector Jobs ==="
    kubectl get jobs -n "$namespace" --sort-by='.metadata.creationTimestamp' || true
}

# Open shell in API pod
open_shell() {
    log_info "Opening shell in API pod..."
    
    # Get first available API pod
    POD=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=stream-sniper-api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    
    if [[ -z "$POD" ]]; then
        log_error "No API pods found in namespace '$namespace'"
        exit 1
    fi
    
    log_info "Connecting to pod: $POD"
    kubectl exec -it "$POD" -n "$namespace" -- /bin/bash
}

# Backup database
backup_database() {
    log_info "Creating database backup..."
    
    # Get PostgreSQL pod
    POSTGRES_POD=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    
    if [[ -z "$POSTGRES_POD" ]]; then
        log_error "No PostgreSQL pods found in namespace '$namespace'"
        exit 1
    fi
    
    BACKUP_FILE="stream-sniper-backup-$(date +%Y%m%d-%H%M%S).sql"
    
    log_info "Creating backup: $BACKUP_FILE"
    kubectl exec "$POSTGRES_POD" -n "$namespace" -- \
        pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"
    
    log_success "Database backup created: $BACKUP_FILE"
}

# Restore database
restore_database() {
    local backup_file="$1"
    
    if [[ -z "$backup_file" ]]; then
        log_error "Backup file required for restore"
        exit 1
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_warning "This will overwrite the current database!"
    read -p "Are you sure you want to continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled"
        exit 0
    fi
    
    # Get PostgreSQL pod
    POSTGRES_POD=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    
    if [[ -z "$POSTGRES_POD" ]]; then
        log_error "No PostgreSQL pods found in namespace '$namespace'"
        exit 1
    fi
    
    log_info "Restoring database from: $backup_file"
    kubectl exec -i "$POSTGRES_POD" -n "$namespace" -- \
        psql -U "$POSTGRES_USER" "$POSTGRES_DB" < "$backup_file"
    
    log_success "Database restored successfully"
}

# Show access information
show_access_info() {
    echo
    log_success "=== Access Information ==="
    
    # Get ingress information
    INGRESS_HOST=$(kubectl get ingress -n "$namespace" -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null || echo "localhost")
    INGRESS_IP=$(kubectl get ingress -n "$namespace" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    echo "API URL: https://$INGRESS_HOST"
    echo "Ingress IP: $INGRESS_IP"
    
    # Port-forward commands
    echo
    echo "Port-forward commands:"
    echo "  API: kubectl port-forward svc/stream-sniper-api-service 8080:80 -n $namespace"
    echo "  Metrics: kubectl port-forward svc/stream-sniper-api-service 9090:8080 -n $namespace"
    echo "  Database: kubectl port-forward svc/postgres-service 5432:5432 -n $namespace"
    echo "  Redis: kubectl port-forward svc/redis-service 6379:6379 -n $namespace"
    
    # Health check
    echo
    echo "Health check:"
    echo "  curl https://$INGRESS_HOST/health"
    echo "  curl https://$INGRESS_HOST/health/detailed"
}

# Parse command line arguments
environment="$DEFAULT_ENVIRONMENT"
namespace="$DEFAULT_NAMESPACE"
image_tag="${IMAGE_TAG:-latest}"
registry="${CONTAINER_REGISTRY:-}"
dry_run="false"
verbose="false"
command=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            environment="$2"
            shift 2
            ;;
        -n|--namespace)
            namespace="$2"
            shift 2
            ;;
        -i|--image)
            image_tag="$2"
            shift 2
            ;;
        -r|--registry)
            registry="$2"
            shift 2
            ;;
        -d|--dry-run)
            dry_run="true"
            shift
            ;;
        -v|--verbose)
            verbose="true"
            set -x
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        deploy|destroy|status|logs|shell|validate|backup|restore)
            command="$1"
            shift
            ;;
        *)
            if [[ -z "$command" ]]; then
                command="$1"
            fi
            shift
            ;;
    esac
done

# Set namespace based on environment
if [[ "$environment" == "development" && "$namespace" == "$DEFAULT_NAMESPACE" ]]; then
    namespace="stream-sniper-dev"
elif [[ "$environment" == "staging" && "$namespace" == "$DEFAULT_NAMESPACE" ]]; then
    namespace="stream-sniper-staging"
fi

# Validate environment
if [[ ! "$environment" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: $environment"
    log_error "Valid environments: development, staging, production"
    exit 1
fi

# Execute command
case $command in
    deploy)
        check_prerequisites
        validate_manifests
        deploy
        ;;
    destroy)
        check_prerequisites
        destroy
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    shell)
        open_shell
        ;;
    validate)
        validate_manifests
        log_success "All manifests validated successfully"
        ;;
    backup)
        backup_database
        ;;
    restore)
        if [[ $# -eq 0 ]]; then
            log_error "Backup file required for restore command"
            echo "Usage: $0 restore <backup-file>"
            exit 1
        fi
        restore_database "$1"
        ;;
    "")
        log_error "No command specified"
        show_help
        exit 1
        ;;
    *)
        log_error "Unknown command: $command"
        show_help
        exit 1
        ;;
esac