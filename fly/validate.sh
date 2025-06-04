#!/bin/bash
# Validation script for unified Stahla deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Stahla Deployment Validation ===${NC}"
echo

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

# Function to check if directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (missing)"
        return 1
    fi
}

validation_failed=0

echo -e "${BLUE}Checking main configuration files:${NC}"
check_file "fly.toml" || validation_failed=1
check_file "Dockerfile" || validation_failed=1
check_file "init.sh" || validation_failed=1
check_file "deploy-unified.sh" || validation_failed=1
check_file "manage-unified.sh" || validation_failed=1
echo

echo -e "${BLUE}Checking application files:${NC}"
check_file "../app/main.py" || validation_failed=1
check_file "../requirements.txt" || validation_failed=1
check_dir "../app/static" || validation_failed=1
check_dir "../app/templates" || validation_failed=1
echo

echo -e "${BLUE}Checking nginx configuration:${NC}"
check_file "old-individual-services/nginx/nginx.conf" || validation_failed=1
check_file "old-individual-services/nginx/default.conf" || validation_failed=1
echo

echo -e "${BLUE}Checking MongoDB initialization:${NC}"
check_file "old-individual-services/mongodb/init.js" || validation_failed=1
check_file "old-individual-services/mongodb/init.sh" || validation_failed=1
echo

echo -e "${BLUE}Checking script permissions:${NC}"
for script in "deploy-unified.sh" "manage-unified.sh" "init.sh"; do
    if [ -x "$script" ]; then
        echo -e "${GREEN}✓${NC} $script (executable)"
    else
        echo -e "${YELLOW}!${NC} $script (not executable, fixing...)"
        chmod +x "$script"
        echo -e "${GREEN}✓${NC} $script (fixed)"
    fi
done
echo

echo -e "${BLUE}Validating fly.toml configuration:${NC}"
if grep -q "app = \"stahla\"" fly.toml; then
    echo -e "${GREEN}✓${NC} App name is correct"
else
    echo -e "${RED}✗${NC} App name is not 'stahla'"
    validation_failed=1
fi

if grep -q "dockerfile = \"./Dockerfile\"" fly.toml; then
    echo -e "${GREEN}✓${NC} Dockerfile path is correct"
else
    echo -e "${RED}✗${NC} Dockerfile path is incorrect"
    validation_failed=1
fi

if grep -q "MONGO_HOST = \"localhost\"" fly.toml; then
    echo -e "${GREEN}✓${NC} MongoDB host is localhost"
else
    echo -e "${RED}✗${NC} MongoDB host should be localhost"
    validation_failed=1
fi

if grep -q "REDIS_URL = \"redis://localhost:6379/0\"" fly.toml; then
    echo -e "${GREEN}✓${NC} Redis URL is localhost"
else
    echo -e "${RED}✗${NC} Redis URL should use localhost"
    validation_failed=1
fi
echo

echo -e "${BLUE}Checking external dependencies:${NC}"
if command -v flyctl &> /dev/null; then
    echo -e "${GREEN}✓${NC} flyctl is installed"
    
    if flyctl auth whoami &> /dev/null; then
        echo -e "${GREEN}✓${NC} flyctl is authenticated"
    else
        echo -e "${YELLOW}!${NC} flyctl is not authenticated (run: flyctl auth login)"
    fi
else
    echo -e "${RED}✗${NC} flyctl is not installed"
    echo -e "${YELLOW}  Install with: curl -L https://fly.io/install.sh | sh${NC}"
    validation_failed=1
fi
echo

# Check Dockerfile syntax
echo -e "${BLUE}Validating Dockerfile:${NC}"
if command -v docker &> /dev/null; then
    if docker build -f Dockerfile --dry-run . &> /dev/null; then
        echo -e "${GREEN}✓${NC} Dockerfile syntax is valid"
    else
        echo -e "${YELLOW}!${NC} Cannot validate Dockerfile (Docker not available or syntax issue)"
    fi
else
    echo -e "${YELLOW}!${NC} Docker not available for Dockerfile validation"
fi
echo

# Summary
if [ $validation_failed -eq 0 ]; then
    echo -e "${GREEN}=== All Validations Passed! ===${NC}"
    echo -e "${GREEN}Your deployment is ready. Run './deploy-unified.sh' to deploy.${NC}"
    echo
    echo -e "${BLUE}Quick start:${NC}"
    echo "1. ./deploy-unified.sh  # Deploy the application"
    echo "2. ./manage-unified.sh status  # Check deployment status"
    echo "3. ./manage-unified.sh logs  # View logs"
    echo "4. Open https://stahla.fly.dev  # Access your application"
else
    echo -e "${RED}=== Validation Failed! ===${NC}"
    echo -e "${RED}Please fix the issues above before deploying.${NC}"
    exit 1
fi
