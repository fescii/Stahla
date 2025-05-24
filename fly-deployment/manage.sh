#!/bin/bash

# Stahla Fly.io Cleanup Script
# This script helps clean up or destroy the Fly.io deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to confirm action
confirm_action() {
    local message="$1"
    echo -e "${YELLOW}[CONFIRM]${NC} $message"
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_status "Operation cancelled"
        exit 0
    fi
}

# Function to stop all services
stop_services() {
    print_status "Stopping all services..."
    
    local apps=("stahla" "stahla-api" "stahla-redis" "stahla-mongodb")
    
    for app in "${apps[@]}"; do
        if fly apps list | grep -q "$app"; then
            print_status "Stopping $app..."
            fly scale count 0 -a "$app" || print_warning "Failed to stop $app"
        fi
    done
    
    print_success "All services stopped"
}

# Function to start all services
start_services() {
    print_status "Starting all services..."
    
    # Start in dependency order
    local apps=("stahla-mongodb" "stahla-redis" "stahla-api" "stahla")
    
    for app in "${apps[@]}"; do
        if fly apps list | grep -q "$app"; then
            print_status "Starting $app..."
            fly scale count 1 -a "$app" || print_warning "Failed to start $app"
            sleep 10  # Wait between services
        fi
    done
    
    print_success "All services started"
}

# Function to destroy all apps and volumes
destroy_deployment() {
    confirm_action "This will PERMANENTLY delete all apps, volumes, and data. This cannot be undone!"
    
    print_status "Destroying Fly.io deployment..."
    
    local apps=("stahla" "stahla-api" "stahla-redis" "stahla-mongodb")
    
    # Stop apps first
    stop_services
    
    # Delete volumes
    print_status "Deleting volumes..."
    
    fly volumes list -a stahla-mongodb | grep "stahla_mongo_data" | awk '{print $1}' | xargs -I {} fly volumes destroy {} -a stahla-mongodb -y || true
    fly volumes list -a stahla-redis | grep "stahla_redis_data" | awk '{print $1}' | xargs -I {} fly volumes destroy {} -a stahla-redis -y || true
    fly volumes list -a stahla-api | grep "stahla_app_data" | awk '{print $1}' | xargs -I {} fly volumes destroy {} -a stahla-api -y || true
    
    # Delete apps
    print_status "Deleting apps..."
    for app in "${apps[@]}"; do
        if fly apps list | grep -q "$app"; then
            print_status "Deleting $app..."
            fly apps destroy "$app" -y || print_warning "Failed to delete $app"
        fi
    done
    
    print_success "Deployment destroyed"
}

# Function to show status
show_status() {
    print_status "Deployment Status:"
    
    local apps=("stahla-mongodb" "stahla-redis" "stahla-api" "stahla")
    
    for app in "${apps[@]}"; do
        echo ""
        if fly apps list | grep -q "$app"; then
            print_status "$app:"
            fly status -a "$app" | head -20
        else
            print_warning "$app: Not found"
        fi
    done
}

# Function to backup MongoDB
backup_mongodb() {
    print_status "Creating MongoDB backup..."
    
    if ! fly apps list | grep -q "stahla-mongodb"; then
        print_error "MongoDB app not found"
        exit 1
    fi
    
    local backup_dir="./mongodb-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    print_status "Creating database dump..."
    fly ssh console -a stahla-mongodb -C "mongodump --out /tmp/backup"
    
    print_status "Downloading backup..."
    cd "$backup_dir"
    fly sftp get /tmp/backup/* . -a stahla-mongodb
    cd ..
    
    print_success "Backup created in: $backup_dir"
}

# Function to restart services
restart_services() {
    print_status "Restarting all services..."
    stop_services
    sleep 10
    start_services
    print_success "All services restarted"
}

# Function to update deployment
update_deployment() {
    print_status "Updating deployment..."
    
    local services=("mongodb" "redis" "api" "nginx")
    
    for service in "${services[@]}"; do
        if [ "$service" = "nginx" ]; then
            local app_name="stahla"
        else
            local app_name="stahla-$service"
        fi
        
        if fly apps list | grep -q "$app_name"; then
            print_status "Updating $app_name..."
            cd "$service"
            fly deploy -a "$app_name"
            cd ..
        fi
    done
    
    print_success "Deployment updated"
}

# Main help function
show_help() {
    echo "Stahla Fly.io Management Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start all services"
    echo "  stop      - Stop all services" 
    echo "  restart   - Restart all services"
    echo "  status    - Show deployment status"
    echo "  backup    - Backup MongoDB data"
    echo "  update    - Update deployment"
    echo "  destroy   - Destroy entire deployment (DANGEROUS)"
    echo "  help      - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 status    # Check current status"
    echo "  $0 backup    # Create MongoDB backup"
    echo "  $0 restart   # Restart all services"
}

# Main script logic
case "${1:-help}" in
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "status")
        show_status
        ;;
    "backup")
        backup_mongodb
        ;;
    "update")
        update_deployment
        ;;
    "destroy")
        destroy_deployment
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
