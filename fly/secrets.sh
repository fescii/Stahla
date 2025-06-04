#!/bin/bash
# Script to read .env file and set Fly.io secrets

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Setting Fly.io Secrets from .env file ===${NC}"

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo -e "${RED}Error: .env file not found in parent directory${NC}"
    exit 1
fi

# Check if fly CLI is available
if ! command -v fly &> /dev/null; then
    echo -e "${RED}Error: fly CLI not found. Please install Fly CLI first.${NC}"
    exit 1
fi

echo -e "${YELLOW}Reading environment variables from .env file...${NC}"

# Read .env file and extract non-commented variables
secrets=""
count=0

while IFS= read -r line; do
    # Skip empty lines and comments
    if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    # Check if line contains an assignment
    if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
        var_name="${BASH_REMATCH[1]}"
        var_value="${BASH_REMATCH[2]}"
        
        # Remove leading/trailing whitespace
        var_name=$(echo "$var_name" | xargs)
        var_value=$(echo "$var_value" | xargs)
        
        # Remove quotes from value if present
        if [[ "$var_value" =~ ^\"(.*)\"$ ]]; then
            var_value="${BASH_REMATCH[1]}"
        fi
        
        # Skip if value is empty or placeholder
        if [[ -z "$var_value" || "$var_value" == "YOUR_"* ]]; then
            echo -e "${YELLOW}Skipping $var_name (empty or placeholder value)${NC}"
            continue
        fi
        
        # Add to secrets string
        if [ -z "$secrets" ]; then
            secrets="$var_name=\"$var_value\""
        else
            secrets="$secrets $var_name=\"$var_value\""
        fi
        
        count=$((count + 1))
        echo -e "${GREEN}✓ Found: $var_name${NC}"
    fi
done < "../.env"

echo
echo -e "${BLUE}Found $count environment variables to set as secrets${NC}"

if [ $count -eq 0 ]; then
    echo -e "${YELLOW}No valid environment variables found to set${NC}"
    exit 0
fi

echo -e "${YELLOW}Setting secrets in Fly.io app 'stahla'...${NC}"

# Set secrets using fly CLI
eval "fly secrets set $secrets --app stahla"

if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}=== Secrets Successfully Set! ===${NC}"
    echo -e "${BLUE}Total secrets set: $count${NC}"
    echo
    echo -e "${YELLOW}You can view the secrets with:${NC}"
    echo "fly secrets list --app stahla"
else
    echo
    echo -e "${RED}=== Failed to Set Secrets! ===${NC}"
    echo "Please check the error messages above and try again."
    exit 1
fi
