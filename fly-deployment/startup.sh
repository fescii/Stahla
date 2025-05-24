#!/bin/bash

# Stahla Fly.io Complete Startup Script
# This script handles the complete deployment and initialization process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/femar/AO3/Stahla"
FLY_DEPLOYMENT_DIR="$PROJECT_ROOT/fly-deployment"
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

print_header() {
    echo -e "${PURPLE}[STAHLA]${NC} $1"
}

# Function to print the banner
print_banner() {
    echo ""
    echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                    STAHLA FLY.IO DEPLOYMENT                   ║${NC}"
    echo -e "${PURPLE}║                   Complete Startup Script                     ║${NC}"
    echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites..."
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env file not found at $ENV_FILE"
        print_error "Please create a .env file with the required variables"
        exit 1
    fi
    print_success ".env file found"
    
    # Check Fly CLI
    if ! command -v fly &> /dev/null; then
        print_error "Fly CLI not found. Installing..."
        curl -L https://fly.io/install.sh | sh
        export PATH="$HOME/.fly/bin:$PATH"
    fi
    print_success "Fly CLI available"
    
    # Check authentication
    if ! fly auth whoami &> /dev/null; then
        print_warning "Not logged in to Fly.io"
        print_status "Please log in to Fly.io..."
        fly auth login
    fi
    print_success "Authenticated with Fly.io"
    
    # Load environment variables
    export $(grep -v '^#' "$ENV_FILE" | xargs)
    print_success "Environment variables loaded"
}

# Function to create Fly apps if they don't exist
create_fly_apps() {
    print_header "Creating Fly.io Applications..."
    
    local apps=("stahla-mongodb" "stahla-redis" "stahla-api" "stahla")
    
    for app in "${apps[@]}"; do
        if fly apps list | grep -q "$app"; then
            print_warning "App $app already exists"
        else
            print_status "Creating app: $app"
            fly apps create "$app"
            print_success "App $app created"
        fi
    done
}

# Function to deploy MongoDB first
deploy_mongodb() {
    print_header "Deploying MongoDB Service..."
    
    cd "$FLY_DEPLOYMENT_DIR/mongodb"
    
    # Create volume if it doesn't exist
    if ! fly volumes list -a stahla-mongodb | grep -q "stahla_mongo_data"; then
        print_status "Creating MongoDB volume..."
        fly volumes create stahla_mongo_data --region sjc --size 10 -a stahla-mongodb
        print_success "MongoDB volume created"
    fi
    
    # Set MongoDB secrets
    print_status "Setting MongoDB secrets..."
    fly secrets set \
        MONGO_INITDB_ROOT_USERNAME="${MONGO_ROOT_USER:-mongoadmin}" \
        MONGO_INITDB_ROOT_PASSWORD="${MONGO_ROOT_PASSWORD:-secret}" \
        MONGO_INITDB_DATABASE="${MONGO_DB_NAME:-stahla_dashboard}" \
        MONGO_USER="${MONGO_USER:-stahla_app}" \
        MONGO_PASSWORD="${MONGO_PASSWORD:-app_password}" \
        -a stahla-mongodb
    
    # Deploy MongoDB
    print_status "Deploying MongoDB..."
    fly deploy --ha=false -a stahla-mongodb
    print_success "MongoDB deployed"
    
    # Wait for MongoDB to be ready
    print_status "Waiting for MongoDB to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if fly ssh console -a stahla-mongodb -C "mongosh --eval 'print(\"ready\")'" >/dev/null 2>&1; then
            print_success "MongoDB is ready"
            break
        fi
        print_status "Waiting for MongoDB... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "MongoDB failed to start properly"
        exit 1
    fi
}

# Function to initialize MongoDB
initialize_mongodb() {
    print_header "Initializing MongoDB Database..."
    
    print_status "Running MongoDB initialization script..."
    "$FLY_DEPLOYMENT_DIR/init-mongodb.sh" init
    
    print_success "MongoDB initialization completed"
}

# Function to deploy other services
deploy_other_services() {
    print_header "Deploying Other Services..."
    
    # Deploy Redis
    print_status "Deploying Redis..."
    cd "$FLY_DEPLOYMENT_DIR/redis"
    
    if ! fly volumes list -a stahla-redis | grep -q "stahla_redis_data"; then
        fly volumes create stahla_redis_data --region sjc --size 3 -a stahla-redis
    fi
    
    fly deploy --ha=false -a stahla-redis
    print_success "Redis deployed"
    
    # Wait for Redis
    sleep 15
    
    # Deploy API
    print_status "Deploying API service..."
    cd "$FLY_DEPLOYMENT_DIR/api"
    
    if ! fly volumes list -a stahla-api | grep -q "stahla_app_data"; then
        fly volumes create stahla_app_data --region sjc --size 5 -a stahla-api
    fi
    
    # Set API secrets
    fly secrets set \
        MONGO_PASSWORD="${MONGO_PASSWORD:-app_password}" \
        MONGO_ROOT_PASSWORD="${MONGO_ROOT_PASSWORD:-secret}" \
        OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
        HUBSPOT_ACCESS_TOKEN="${HUBSPOT_ACCESS_TOKEN:-}" \
        BLAND_API_KEY="${BLAND_API_KEY:-}" \
        GOOGLE_MAPS_API_KEY="${GOOGLE_MAPS_API_KEY:-}" \
        JWT_SECRET_KEY="${JWT_SECRET_KEY:-default_secret_key}" \
        -a stahla-api
    
    fly deploy --ha=false -a stahla-api
    print_success "API deployed"
    
    # Wait for API
    sleep 20
    
    # Deploy Nginx
    print_status "Deploying Nginx..."
    cd "$FLY_DEPLOYMENT_DIR/nginx"
    fly deploy --ha=false -a stahla
    print_success "Nginx deployed"
}

# Function to verify deployment
verify_deployment() {
    print_header "Verifying Deployment..."
    
    local services=("stahla-mongodb" "stahla-redis" "stahla-api" "stahla")
    
    for service in "${services[@]}"; do
        print_status "Checking $service status..."
        if fly status -a "$service" | grep -q "running"; then
            print_success "$service is running"
        else
            print_warning "$service may not be running properly"
        fi
    done
    
    # Test MongoDB connection
    print_status "Verifying MongoDB setup..."
    "$FLY_DEPLOYMENT_DIR/init-mongodb.sh" verify
    
    # Test API endpoint
    print_status "Testing API endpoint..."
    if curl -s "https://stahla-api.fly.dev/health" >/dev/null; then
        print_success "API is responding"
    else
        print_warning "API may not be responding yet"
    fi
    
    # Test Nginx
    print_status "Testing Nginx proxy..."
    if curl -s "https://stahla.fly.dev/health" >/dev/null; then
        print_success "Nginx is responding"
    else
        print_warning "Nginx may not be responding yet"
    fi
}

# Function to display final information
display_final_info() {
    print_header "Deployment Complete!"
    
    echo ""
    print_success "Your Stahla application is now deployed on Fly.io!"
    echo ""
    print_status "Service URLs:"
    echo "  • Main Application: https://stahla.fly.dev"
    echo "  • API Direct: https://stahla-api.fly.dev"
    echo "  • MongoDB: stahla-mongodb.internal:27017"
    echo "  • Redis: stahla-redis.internal:6379"
    echo ""
    print_status "MongoDB Connection String:"
    if [ -f "$PROJECT_ROOT/mongodb_url.env" ]; then
        cat "$PROJECT_ROOT/mongodb_url.env"
    else
        echo "  mongodb://${MONGO_USER:-stahla_app}:${MONGO_PASSWORD:-app_password}@stahla-mongodb.internal:27017/${MONGO_DB_NAME:-stahla_dashboard}"
    fi
    echo ""
    print_status "Useful Commands:"
    echo "  • Check status: fly status -a <app-name>"
    echo "  • View logs: fly logs -a <app-name>"
    echo "  • SSH to service: fly ssh console -a <app-name>"
    echo "  • Scale service: fly scale count 2 -a <app-name>"
    echo ""
    print_warning "Note: It may take a few minutes for all services to be fully ready."
    echo ""
}

# Function to cleanup on error
cleanup_on_error() {
    print_error "Deployment failed. Cleaning up..."
    # Add any cleanup logic here if needed
}

# Main function
main() {
    # Set error handler
    trap cleanup_on_error ERR
    
    print_banner
    
    print_header "Starting Complete Stahla Deployment..."
    
    # Step 1: Prerequisites
    check_prerequisites
    
    # Step 2: Create Fly apps
    create_fly_apps
    
    # Step 3: Deploy MongoDB first (most critical)
    deploy_mongodb
    
    # Step 4: Initialize MongoDB
    initialize_mongodb
    
    # Step 5: Deploy other services
    deploy_other_services
    
    # Step 6: Verify deployment
    verify_deployment
    
    # Step 7: Display final information
    display_final_info
    
    print_success "Deployment process completed successfully!"
}

# Script options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "mongodb-only")
        print_banner
        check_prerequisites
        create_fly_apps
        deploy_mongodb
        initialize_mongodb
        display_final_info
        ;;
    "verify")
        check_prerequisites
        verify_deployment
        ;;
    "status")
        "$FLY_DEPLOYMENT_DIR/deploy.sh" status
        ;;
    "help")
        echo "Usage: $0 [deploy|mongodb-only|verify|status|help]"
        echo "  deploy       - Full deployment (default)"
        echo "  mongodb-only - Deploy and initialize MongoDB only"
        echo "  verify       - Verify deployment"
        echo "  status       - Check deployment status"
        echo "  help         - Show this help"
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
