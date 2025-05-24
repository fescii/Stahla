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

# Initialize MongoDB if not already initialized
if [ ! -f /data/mongodb/mongod.lock ]; then
    echo "Initializing MongoDB..."
    
    # Start MongoDB temporarily for initialization
    mongod --dbpath /data/mongodb --logpath /data/logs/mongodb-init.log --fork --bind_ip_all
    
    # Wait for MongoDB to start
    sleep 10
    
    # Run initialization script
    if [ -f ./init-mongo.sh ]; then
        chmod +x ./init-mongo.sh
        ./init-mongo.sh
        echo "MongoDB initialized with users and collections"
    else
        echo "Warning: MongoDB initialization script not found"
    fi
    
    # Stop temporary MongoDB instance
    mongod --dbpath /data/mongodb --shutdown
    
    echo "MongoDB initialization completed"
else
    echo "MongoDB already initialized, skipping..."
fi

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

# If this script is run as the main command, start a process supervisor
if [ "$1" = "--supervisor" ]; then
    echo "Starting process supervisor mode..."
    
    # Start MongoDB
    echo "Starting MongoDB..."
    mongod --auth --bind_ip_all --dbpath /data/mongodb --logpath /data/logs/mongodb.log --fork
    
    # Start Redis
    echo "Starting Redis..."
    redis-server /etc/redis/redis.conf --daemonize yes
    
    # Wait for services to be ready
    sleep 10
    
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
