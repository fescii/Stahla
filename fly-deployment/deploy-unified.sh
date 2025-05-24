#!/bin/bash
# Simplified deployment script for single Stahla Fly.io app
# Deploy everything as one unified application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default organization (can be overridden)
ORG_NAME="sdr-ai-agent"

# Check for organization parameter
if [ "$1" = "--org" ] && [ -n "$2" ]; then
    ORG_NAME="$2"
    echo -e "${BLUE}Using organization: ${ORG_NAME}${NC}"
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo -e "${BLUE}=== Stahla Unified Deployment Script ===${NC}"
    echo
    echo "Usage: $0 [--org ORGANIZATION_NAME]"
    echo
    echo "Options:"
    echo "  --org ORG_NAME    Deploy to a specific Fly.io organization"
    echo "  --help, -h        Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Deploy to personal account"
    echo "  $0 --org mycompany    # Deploy to 'mycompany' organization"
    echo
    echo "To list your organizations, run: flyctl orgs list"
    exit 0
fi

echo -e "${BLUE}=== Stahla Unified Deployment Script ===${NC}"
echo

# Change to parent directory for proper build context
cd ..

# Check if we're in the right directory (should have fly-deployment subdirectory)
if [ ! -d "fly-deployment" ] || [ ! -f "fly-deployment/fly.toml" ]; then
    echo -e "${RED}Error: fly-deployment/fly.toml not found. Please run this script from the fly-deployment directory.${NC}"
    exit 1
fi

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo -e "${RED}Error: flyctl is not installed. Please install it first:${NC}"
    echo "curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if user is authenticated
if ! flyctl auth whoami &> /dev/null; then
    echo -e "${YELLOW}You are not authenticated with Fly.io. Please log in:${NC}"
    flyctl auth login
fi

# Show available organizations
echo -e "${BLUE}Available organizations:${NC}"
flyctl orgs list | grep -E "^(Name|----)" || echo "Unable to list organizations"
echo

echo -e "${BLUE}Step 1: Creating Fly.io app if it doesn't exist${NC}"
echo "Using organization: ${ORG_NAME}"

# Check if app exists, create if it doesn't
if ! flyctl status --app stahla &> /dev/null; then
    echo "App 'stahla' doesn't exist. Creating it in organization '${ORG_NAME}'..."
    if flyctl apps create stahla --org "${ORG_NAME}"; then
        echo -e "${GREEN}✓ App 'stahla' created successfully in organization '${ORG_NAME}'${NC}"
    else
        echo -e "${RED}✗ Failed to create app 'stahla' in organization '${ORG_NAME}'${NC}"
        echo "This might be because:"
        echo "• The app name 'stahla' is already taken by another user"
        echo "• You don't have permission to create apps in organization '${ORG_NAME}'"
        echo "• The organization '${ORG_NAME}' doesn't exist or you're not a member"
        echo "• Your account has reached the app limit"
        echo
        echo -e "${YELLOW}Suggestions:${NC}"
        echo "• Try a different organization: $0 --org <org-name>"
        echo "• List your organizations: flyctl orgs list"
        echo "• Use a different app name by editing fly.toml"
        echo "• Add a payment method if you've hit the free tier limit"
        echo "• Network connectivity issues"
        echo
        echo "Please try a different app name or check your Fly.io account."
        exit 1
    fi
else
    echo -e "${GREEN}✓ App 'stahla' already exists${NC}"
fi
echo

echo -e "${BLUE}Step 2: Creating volume for persistent data${NC}"
echo "Checking if volume 'stahla_data' exists..."
if flyctl volumes list --app stahla 2>/dev/null | grep -q "stahla_data"; then
    echo -e "${GREEN}✓ Volume 'stahla_data' already exists${NC}"
else
    echo "Creating new volume 'stahla_data'..."
    if flyctl volumes create stahla_data --size 10 --region sjc --app stahla; then
        echo -e "${GREEN}✓ Volume 'stahla_data' created successfully${NC}"
    else
        echo -e "${RED}✗ Failed to create volume${NC}"
        echo "Please check your Fly.io account and try again."
        exit 1
    fi
fi
echo

echo -e "${BLUE}Step 3: Deploying the Stahla application${NC}"
echo "This will build and deploy the unified application with all services..."
flyctl deploy --app stahla --verbose --config fly-deployment/fly.toml

if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}=== Deployment Successful! ===${NC}"
    echo
    echo -e "${BLUE}Application Details:${NC}"
    echo "• App Name: stahla"
    echo "• URL: https://stahla.fly.dev"
    echo "• Health Check: https://stahla.fly.dev/health"
    echo
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "• Check status: flyctl status --app stahla"
    echo "• View logs: flyctl logs --app stahla"
    echo "• Scale app: flyctl scale count 1 --app stahla"
    echo "• SSH into app: flyctl ssh console --app stahla"
    echo
    echo -e "${YELLOW}Note: It may take a few minutes for all services to fully start up.${NC}"
    echo -e "${YELLOW}Monitor the logs to ensure MongoDB, Redis, API, and Nginx are all running.${NC}"
else
    echo
    echo -e "${RED}=== Deployment Failed! ===${NC}"
    echo "Check the error messages above and try again."
    exit 1
fi
