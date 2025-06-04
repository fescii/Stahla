#!/bin/bash

# Stahla Fly.io Deployment Script
# This script deploys the complete multi-service application to Fly.io

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/femar/AO3/Stahla"
FLY_DEPLOYMENT_DIR="$PROJECT_ROOT/fly"
ENV_FILE="$PROJECT_ROOT/.env"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env file not found at $ENV_FILE"
        print_error "Please create a .env file with the required variables"
        exit 1
    fi
    print_success ".env file found"
}

# Function to load environment variables
load_env() {
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
        print_success "Environment variables loaded"
    fi
}

# Function to check if fly CLI is installed
check_fly_cli() {
    if ! command -v fly &> /dev/null; then
        print_error "Fly CLI not found. Please install it first:"
        print_error "curl -L https://fly.io/install.sh | sh"
        exit 1
    fi
    print_success "Fly CLI found"
}

# Function to check if user is logged in to Fly.io
check_fly_auth() {
    if ! fly auth whoami &> /dev/null; then
        print_error "Not logged in to Fly.io. Please run: fly auth login"
        exit 1
    fi
    print_success "Authenticated with Fly.io"
}

# Function to create Fly.io volumes
create_volumes() {
    print_status "Creating Fly.io volumes..."
    
    # MongoDB volume
    print_status "Creating MongoDB volume..."
    if fly volumes list -a stahla-mongodb | grep -q "stahla_mongo_data"; then
        print_warning "MongoDB volume already exists"
    else
        fly volumes create stahla_mongo_data --region sjc --size 10 -a stahla-mongodb
        print_success "MongoDB volume created"
    fi
    
    # Redis volume
    print_status "Creating Redis volume..."
    if fly volumes list -a stahla-redis | grep -q "stahla_redis_data"; then
        print_warning "Redis volume already exists"
    else
        fly volumes create stahla_redis_data --region sjc --size 3 -a stahla-redis
        print_success "Redis volume created"
    fi
    
    # API volume
    print_status "Creating API volume..."
    if fly volumes list -a stahla-api | grep -q "stahla_app_data"; then
        print_warning "API volume already exists"
    else
        fly volumes create stahla_app_data --region sjc --size 5 -a stahla-api
        print_success "API volume created"
    fi
}

# Function to set secrets
set_secrets() {
    print_status "Setting secrets for each service..."
    
    # MongoDB secrets
    print_status "Setting MongoDB secrets..."
    fly secrets set \
        MONGO_INITDB_ROOT_USERNAME="${MONGO_ROOT_USER:-mongoadmin}" \
        MONGO_INITDB_ROOT_PASSWORD="${MONGO_ROOT_PASSWORD:-secret}" \
        MONGO_USER="${MONGO_USER:-stahla_app}" \
        MONGO_PASSWORD="${MONGO_PASSWORD:-app_password}" \
        -a stahla-mongodb
    
    # API secrets
    print_status "Setting API secrets..."
    fly secrets set \
        MONGO_PASSWORD="${MONGO_PASSWORD:-app_password}" \
        MONGO_ROOT_PASSWORD="${MONGO_ROOT_PASSWORD:-secret}" \
        OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
        HUBSPOT_ACCESS_TOKEN="${HUBSPOT_ACCESS_TOKEN:-}" \
        BLAND_API_KEY="${BLAND_API_KEY:-}" \
        GOOGLE_MAPS_API_KEY="${GOOGLE_MAPS_API_KEY:-}" \
        JWT_SECRET_KEY="${JWT_SECRET_KEY:-default_secret_key}" \
        -a stahla-api
    
    print_success "Secrets set successfully"
}

# Function to deploy services in order
deploy_services() {
    print_status "Deploying services in dependency order..."
    
    # 1. Deploy MongoDB first
    print_status "Deploying MongoDB..."
    cd "$FLY_DEPLOYMENT_DIR/mongodb"
    fly deploy --ha=false
    print_success "MongoDB deployed"
    
    # Wait for MongoDB to be ready
    print_status "Waiting for MongoDB to be ready..."
    sleep 30
    
    # 2. Deploy Redis
    print_status "Deploying Redis..."
    cd "$FLY_DEPLOYMENT_DIR/redis"
    fly deploy --ha=false
    print_success "Redis deployed"
    
    # Wait for Redis to be ready
    print_status "Waiting for Redis to be ready..."
    sleep 15
    
    # 3. Deploy API
    print_status "Deploying API..."
    cd "$FLY_DEPLOYMENT_DIR/api"
    fly deploy --ha=false
    print_success "API deployed"
    
    # Wait for API to be ready
    print_status "Waiting for API to be ready..."
    sleep 20
    
    # 4. Deploy Nginx
    print_status "Deploying Nginx..."
    cd "$FLY_DEPLOYMENT_DIR/nginx"
    fly deploy --ha=false
    print_success "Nginx deployed"
    
    print_success "All services deployed successfully!"
}

# Function to initialize MongoDB
initialize_mongodb() {
    print_status "Initializing MongoDB..."
    
    # Connect to MongoDB and run initialization
    print_status "Connecting to MongoDB to verify initialization..."
    
    # Get MongoDB connection string
    MONGO_URL="mongodb://${MONGO_USER:-stahla_app}:${MONGO_PASSWORD:-app_password}@stahla-mongodb.internal:27017/${MONGO_DB_NAME:-stahla_dashboard}"
    
    print_success "MongoDB initialization completed"
    print_status "MongoDB URL for your application: $MONGO_URL"
}

# Function to show deployment status
show_status() {
    print_status "Checking deployment status..."
    
    echo ""
    print_status "MongoDB Status:"
    fly status -a stahla-mongodb
    
    echo ""
    print_status "Redis Status:"
    fly status -a stahla-redis
    
    echo ""
    print_status "API Status:"
    fly status -a stahla-api
    
    echo ""
    print_status "Nginx Status:"
    fly status -a stahla
    
    echo ""
    print_success "Deployment Status Check Complete!"
    print_status "Your application should be available at: https://stahla.fly.dev"
}

# Main deployment function
main() {
    print_status "Starting Stahla Fly.io Deployment..."
    
    # Pre-deployment checks
    check_env_file
    load_env
    check_fly_cli
    check_fly_auth
    
    # Create volumes
    create_volumes
    
    # Set secrets
    set_secrets
    
    # Deploy services
    deploy_services
    
    # Initialize MongoDB
    initialize_mongodb
    
    # Show status
    show_status
    
    print_success "Deployment completed successfully!"
    print_status "Next steps:"
    print_status "1. Verify all services are running: fly status -a <app-name>"
    print_status "2. Check logs if needed: fly logs -a <app-name>"
    print_status "3. Access your application at: https://stahla.fly.dev"
}

# Script options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "status")
        show_status
        ;;
    "secrets")
        check_env_file
        load_env
        set_secrets
        ;;
    "volumes")
        create_volumes
        ;;
    "help")
        echo "Usage: $0 [deploy|status|secrets|volumes|help]"
        echo "  deploy  - Full deployment (default)"
        echo "  status  - Check deployment status"
        echo "  secrets - Set secrets only"
        echo "  volumes - Create volumes only"
        echo "  help    - Show this help"
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
