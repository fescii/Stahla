#!/bin/bash
# Management script for unified Stahla Fly.io application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

APP_NAME="stahla"

show_help() {
    echo -e "${BLUE}Stahla Unified App Management Script${NC}"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  status      - Show application status"
    echo "  logs        - Show application logs (all services)"
    echo "  logs-api    - Show only API logs"
    echo "  logs-nginx  - Show only Nginx logs"
    echo "  ssh         - SSH into the application"
    echo "  restart     - Restart the application"
    echo "  scale       - Scale the application"
    echo "  info        - Show detailed app information"
    echo "  secrets     - Manage application secrets"
    echo "  volumes     - Manage application volumes"
    echo "  health      - Check application health"
    echo "  destroy     - Destroy the application (CAREFUL!)"
    echo "  help        - Show this help message"
    echo
}

check_app_exists() {
    if ! flyctl apps list | grep -q "^$APP_NAME"; then
        echo -e "${RED}Error: App '$APP_NAME' does not exist.${NC}"
        echo "Run deploy-unified.sh to create and deploy the app first."
        exit 1
    fi
}

case "$1" in
    "status")
        check_app_exists
        echo -e "${BLUE}=== Application Status ===${NC}"
        flyctl status --app $APP_NAME
        ;;
    
    "logs")
        check_app_exists
        echo -e "${BLUE}=== Application Logs (All Services) ===${NC}"
        flyctl logs --app $APP_NAME
        ;;
    
    "logs-api")
        check_app_exists
        echo -e "${BLUE}=== API Logs ===${NC}"
        flyctl logs --app $APP_NAME | grep -E "(uvicorn|fastapi|api)"
        ;;
    
    "logs-nginx")
        check_app_exists
        echo -e "${BLUE}=== Nginx Logs ===${NC}"
        flyctl logs --app $APP_NAME | grep -E "(nginx)"
        ;;
    
    "ssh")
        check_app_exists
        echo -e "${BLUE}=== SSH into Application ===${NC}"
        flyctl ssh console --app $APP_NAME
        ;;
    
    "restart")
        check_app_exists
        echo -e "${BLUE}=== Restarting Application ===${NC}"
        flyctl apps restart $APP_NAME
        echo -e "${GREEN}✓ Application restarted${NC}"
        ;;
    
    "scale")
        check_app_exists
        echo -e "${BLUE}=== Current Scale ===${NC}"
        flyctl scale show --app $APP_NAME
        echo
        echo -e "${YELLOW}To scale, use: flyctl scale count [NUMBER] --app $APP_NAME${NC}"
        echo -e "${YELLOW}To change VM size, use: flyctl scale vm [SIZE] --app $APP_NAME${NC}"
        ;;
    
    "info")
        check_app_exists
        echo -e "${BLUE}=== Application Information ===${NC}"
        flyctl info --app $APP_NAME
        echo
        echo -e "${BLUE}=== Application Configuration ===${NC}"
        flyctl config show --app $APP_NAME
        ;;
    
    "secrets")
        check_app_exists
        echo -e "${BLUE}=== Application Secrets ===${NC}"
        echo "Current secrets:"
        flyctl secrets list --app $APP_NAME
        echo
        echo -e "${YELLOW}To set a secret: flyctl secrets set KEY=value --app $APP_NAME${NC}"
        echo -e "${YELLOW}To remove a secret: flyctl secrets unset KEY --app $APP_NAME${NC}"
        ;;
    
    "volumes")
        check_app_exists
        echo -e "${BLUE}=== Application Volumes ===${NC}"
        flyctl volumes list --app $APP_NAME
        echo
        echo -e "${YELLOW}To create a volume: flyctl volumes create [NAME] --size [GB] --app $APP_NAME${NC}"
        ;;
    
    "health")
        check_app_exists
        echo -e "${BLUE}=== Health Check ===${NC}"
        echo "Checking application health..."
        
        # Check if app is responding
        if curl -s -f "https://$APP_NAME.fly.dev/health" > /dev/null; then
            echo -e "${GREEN}✓ Application is responding${NC}"
            echo "Response:"
            curl -s "https://$APP_NAME.fly.dev/health" | jq . 2>/dev/null || curl -s "https://$APP_NAME.fly.dev/health"
        else
            echo -e "${RED}✗ Application is not responding${NC}"
            echo "Check logs for more information:"
            echo "flyctl logs --app $APP_NAME"
        fi
        ;;
    
    "destroy")
        check_app_exists
        echo -e "${RED}=== DESTROY APPLICATION ===${NC}"
        echo -e "${YELLOW}This will permanently delete the application and all its data!${NC}"
        echo -e "${YELLOW}This action cannot be undone!${NC}"
        echo
        read -p "Are you sure you want to destroy the app '$APP_NAME'? Type 'YES' to confirm: " confirm
        
        if [ "$confirm" = "YES" ]; then
            echo "Destroying application..."
            flyctl apps destroy $APP_NAME --yes
            echo -e "${GREEN}✓ Application destroyed${NC}"
        else
            echo "Destruction cancelled."
        fi
        ;;
    
    "help" | "-h" | "--help" | "")
        show_help
        ;;
    
    *)
        echo -e "${RED}Error: Unknown command '$1'${NC}"
        echo
        show_help
        exit 1
        ;;
esac
