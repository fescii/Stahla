#!/bin/bash
# Unified initialization script for all services in the Stahla Fly.io app

set -e

echo "Starting Stahla unified initialization..."

# Create required directories
mkdir -p /data/mongodb /data/redis /data/logs
mkdir -p /var/log/nginx

# Set proper permissions
chown -R mongodb:mongodb /data/mongodb
chown -R redis:redis /data/redis
chown -R www-data:www-data /var/log/nginx

echo "Directories created and permissions set"

# MongoDB user management is now handled manually via SSH console
# This avoids automatic user creation conflicts and provides better control

# Initialize MongoDB directories only (no automatic user creation)
echo "Setting up MongoDB directories..."
mkdir -p /data/mongodb /data/logs
chown -R mongodb:mongodb /data/mongodb
echo "MongoDB directory setup completed - users managed manually via SSH"

# Initialize Redis configuration
echo "Configuring Redis..."
cat > /etc/redis/redis.conf << EOF
# Redis configuration for Fly.io deployment
bind 127.0.0.1
port 6379
appendonly yes
dir /data/redis
logfile /data/logs/redis.log
save 900 1
save 300 10
save 60 10000
maxmemory 256mb
maxmemory-policy allkeys-lru
EOF

echo "Redis configured"

# Test Nginx configuration
echo "Testing Nginx configuration..."
nginx -t
if [ $? -eq 0 ]; then
    echo "Nginx configuration is valid"
else
    echo "Error: Nginx configuration is invalid"
    exit 1
fi

echo "All services initialized successfully"

# Function to verify MongoDB connection
verify_mongodb_connection() {
    echo "Verifying MongoDB connection..."
    
    # Test connection parameters
    MONGO_HOST="${MONGO_HOST:-localhost}"
    MONGO_PORT="${MONGO_PORT:-27017}"
    MONGO_DB="${MONGO_DB_NAME:-admin}"
    MONGO_USER="${MONGO_USER:-stahla}"
    MONGO_PASS="${MONGO_PASSWORD:-Stahla@2024}"
    
    echo "Testing MongoDB connection to: ${MONGO_HOST}:${MONGO_PORT}"
    echo "Database: ${MONGO_DB}"
    echo "User: ${MONGO_USER}"
    
    # Test 1: Check if MongoDB process is running
    if pgrep mongod > /dev/null; then
        echo "✓ MongoDB process is running"
    else
        echo "✗ MongoDB process is not running"
        return 1
    fi
    
    # Test 2: Check if MongoDB port is listening
    if ss -tuln 2>/dev/null | grep ":${MONGO_PORT}" > /dev/null || lsof -i :${MONGO_PORT} 2>/dev/null | grep -q LISTEN; then
        echo "✓ MongoDB is listening on port ${MONGO_PORT}"
    else
        echo "✗ MongoDB is not listening on port ${MONGO_PORT}"
        echo "Checking for any MongoDB ports..."
        ss -tuln 2>/dev/null | grep ":27017" || lsof -i :27017 2>/dev/null || echo "No MongoDB ports found"
        return 1
    fi
    
    # Test 3: Test MongoDB connection with authentication
    echo "Testing MongoDB authentication..."
    CONNECTION_TEST=$(mongosh --host "${MONGO_HOST}" --port "${MONGO_PORT}" \
        --username "${MONGO_USER}" --password "${MONGO_PASS}" \
        --authenticationDatabase "${MONGO_DB}" \
        --eval "db.runCommand({ping: 1})" \
        --quiet 2>&1)
    
    if echo "$CONNECTION_TEST" | grep -q '"ok" : 1'; then
        echo "✓ MongoDB authentication successful"
        
        # Test 4: List available databases
        echo "Available databases:"
        mongosh --host "${MONGO_HOST}" --port "${MONGO_PORT}" \
            --username "${MONGO_USER}" --password "${MONGO_PASS}" \
            --authenticationDatabase "${MONGO_DB}" \
            --eval "db.adminCommand('listDatabases')" \
            --quiet 2>/dev/null || echo "Could not list databases"
            
        # Test 5: Check users in the target database
        echo "Users in ${MONGO_DB} database:"
        mongosh --host "${MONGO_HOST}" --port "${MONGO_PORT}" \
            --username "${MONGO_USER}" --password "${MONGO_PASS}" \
            --authenticationDatabase "${MONGO_DB}" \
            --eval "use ${MONGO_DB}; db.runCommand({usersInfo: 1})" \
            --quiet 2>/dev/null || echo "Could not list users"
            
        return 0
    else
        echo "✗ MongoDB authentication failed"
        echo "Connection test output: $CONNECTION_TEST"
        
        # Try connecting without authentication to diagnose
        echo "Attempting connection without authentication..."
        NO_AUTH_TEST=$(mongosh --host "${MONGO_HOST}" --port "${MONGO_PORT}" \
            --eval "db.runCommand({ping: 1})" \
            --quiet 2>&1)
        
        if echo "$NO_AUTH_TEST" | grep -q '"ok" : 1'; then
            echo "✓ MongoDB connection works without authentication"
            echo "Issue: Authentication credentials may be incorrect"
        else
            echo "✗ MongoDB connection failed even without authentication"
            echo "Output: $NO_AUTH_TEST"
        fi
        
        return 1
    fi
}

# If this script is run as the main command, start a process supervisor
if [ "$1" = "--supervisor" ]; then
    echo "Starting process supervisor mode..."
    
    # Start MongoDB
    echo "Starting MongoDB..."
    mongod --auth --bind_ip 0.0.0.0 --dbpath /data/mongodb --logpath /data/logs/mongodb.log --fork
    
    # Start Redis
    echo "Starting Redis..."
    redis-server /etc/redis/redis.conf --daemonize yes
    
    # Wait for services to be ready
    sleep 10
    
    # Verify MongoDB connection before starting the application
    if verify_mongodb_connection; then
        echo "✓ MongoDB verification successful - proceeding with application startup"
    else
        echo "✗ MongoDB verification failed - application may not start correctly"
        echo "Continuing anyway for debugging purposes..."
    fi
    
    # Start FastAPI
    echo "Starting FastAPI application..."
    cd /app
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    
    # Wait for API to be ready
    sleep 5
    
    # Start Nginx
    echo "Starting Nginx..."
    nginx -g 'daemon off;' &
    
    # Keep container running
    wait
else
    echo "Initialization complete. Services can be started individually."
fi
