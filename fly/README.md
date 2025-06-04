# Stahla Fly.io Deployment

This directory contains all the necessary files and scripts to deploy the complete Stahla application stack to Fly.io as a **single unified application**.

## Architecture

The application runs as a single Fly.io app (`stahla`) containing multiple services:

1. **MongoDB** - Database service with authentication
2. **Redis** - Caching and session storage
3. **FastAPI** - Main application API
4. **Nginx** - Reverse proxy and static file server

All services run within the same machine and communicate via localhost, providing:

- Simplified deployment and management
- Lower resource usage
- Faster inter-service communication
- Single domain: `https://stahla.fly.dev`

### Service Details

#### MongoDB

- **Port**: 27017 (internal)
- **Authentication**: Enabled with app-specific user
- **Data**: Persistent storage via Fly.io volume
- **Initialization**: Automatic database and user setup

#### Redis

- **Port**: 6379 (internal)
- **Storage**: Persistent via volume
- **Configuration**: Optimized for caching

#### FastAPI

- **Port**: 8000 (internal)
- **Framework**: Python FastAPI application
- **Features**: API endpoints, health checks

#### Nginx

- **Port**: 80/443 (external)
- **Routing**:
  - `/` → FastAPI
  - `/api/` → FastAPI
  - `/static/` → Static files
  - `/health` → Health check

## Prerequisites

1. **Fly.io CLI** - Install from https://fly.io/install.sh
2. **Fly.io Account** - Sign up at https://fly.io
3. **Environment Variables** - Create a `.env` file in the project root

### Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# MongoDB Configuration
MONGO_ROOT_USER=mongoadmin
MONGO_ROOT_PASSWORD=your_secure_root_password
MONGO_USER=stahla_app
MONGO_PASSWORD=your_secure_app_password
MONGO_DB_NAME=stahla_dashboard
MONGO_HOST=localhost
MONGO_PORT=27017

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Keys (Optional but recommended)
OPENAI_API_KEY=your_openai_api_key
HUBSPOT_ACCESS_TOKEN=your_hubspot_token
BLAND_API_KEY=your_bland_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_key

# Security
JWT_SECRET_KEY=your_jwt_secret_key

# Application Configuration
APP_BASE_URL=http://localhost:8000
API_V1_STR=/api/v1
```

## Quick Start

### Unified Deployment (Recommended)

Deploy the entire application as a single unified Fly.io app:

```bash
cd fly-deployment
./deploy-unified.sh
```

This script will:

1. Check prerequisites and Fly.io authentication
2. Create the unified Fly.io app (`stahla`)
3. Create persistent volume for data storage
4. Build and deploy all services in one container
5. Initialize MongoDB with proper users and collections
6. Configure Redis, API, and Nginx services
7. Make the application available at `https://stahla.fly.dev`

### Manual Deployment Steps

If you prefer step-by-step deployment:

```bash
# 1. Authenticate with Fly.io
flyctl auth login

# 2. Create the app (optional - deploy will create it)
flyctl apps create stahla

# 3. Create persistent volume
flyctl volumes create stahla_data --size 10 --region sjc --app stahla

# 4. Deploy the application
flyctl deploy --app stahla
```

6. Configure Redis, API, and Nginx services
7. Make the application available at `https://stahla.fly.dev`

### Manual Deployment Steps

If you prefer step-by-step deployment:

```bash
# 1. Authenticate with Fly.io
flyctl auth login

# 2. Create the app (optional - deploy will create it)
flyctl apps create stahla

# 3. Create persistent volume
flyctl volumes create stahla_data --size 10 --region sjc --app stahla

# 4. Deploy the application
flyctl deploy --app stahla
```

## Application Management

Use the unified management script for all operations:

```bash
# Check application status
./manage-unified.sh status

# View logs (all services)
./manage-unified.sh logs

# View specific service logs
./manage-unified.sh logs-api
./manage-unified.sh logs-nginx

# SSH into the application
./manage-unified.sh ssh

# Restart the application
./manage-unified.sh restart

# Check health
./manage-unified.sh health

# View detailed information
./manage-unified.sh info

# Get help
./manage-unified.sh help
```

### Direct Fly.io Commands

You can also use flyctl directly:

```bash
# Check status
flyctl status --app stahla

# View logs
flyctl logs --app stahla

# SSH into the machine
flyctl ssh console --app stahla

# Scale the application
flyctl scale count 2 --app stahla
flyctl scale vm shared-cpu-2x --app stahla
```

## Service Configuration

### Unified Application (`stahla`)

The single Fly.io app contains all services running together:

#### MongoDB

- **Version**: MongoDB 7
- **Port**: 27017 (localhost)
- **Data**: Stored in `/data/mongodb` on persistent volume
- **Authentication**: Enabled with dedicated app user
- **Initialization**: Automatic setup on first deployment

#### Redis

- **Port**: 6379 (localhost)
- **Data**: Stored in `/data/redis` on persistent volume
- **Configuration**: Optimized for caching with persistence

#### FastAPI

- **Port**: 8000 (localhost)
- **Framework**: Python FastAPI
- **Dependencies**: All Python packages from requirements.txt

#### Nginx

- **Port**: 80/443 (external)
- **SSL**: Automatic via Fly.io
- **Static Files**: Served directly
- **Proxy**: Routes API requests to FastAPI

## Network Architecture

```
Internet → Fly.io → stahla.fly.dev (Nginx:80/443)
                         ↓
                    FastAPI (localhost:8000)
                         ↓
               ┌─────────┴─────────┐
               ↓                   ↓
        MongoDB (localhost:27017)  Redis (localhost:6379)
```

### Internal Communication

- All services communicate via `localhost`
- No network latency between services
- Simplified configuration and security
  FastAPI (stahla-api.internal:8000)
  ↓
  ┌── MongoDB (stahla-mongodb.internal:27017)
  └── Redis (stahla-redis.internal:6379)

```

## Important Files

### Configuration Files

- `api/fly.toml` - FastAPI service configuration
- `mongodb/fly.toml` - MongoDB service configuration
- `redis/fly.toml` - Redis service configuration
- `nginx/fly.toml` - Nginx service configuration

### Internal Communication
- All services communicate via `localhost`
- No network latency between services
- Simplified configuration and security

## File Structure

### Configuration Files

- `fly.toml` - Main Fly.io application configuration
- `Dockerfile` - Unified container with all services
- `init.sh` - Service initialization script

### Nginx Configuration

- `old-individual-services/nginx/nginx.conf` - Nginx main configuration
- `old-individual-services/nginx/default.conf` - Nginx site configuration

### MongoDB Initialization

- `old-individual-services/mongodb/init-mongo-fly.sh` - MongoDB setup script
- `old-individual-services/mongodb/init-mongo-fly.js` - MongoDB collections and users

### Deployment Scripts

- `deploy-unified.sh` - Complete unified deployment
- `manage-unified.sh` - Application management script

## Post-Deployment

### Accessing Your Application

- **Main Application**: https://stahla.fly.dev
- **Health Check**: https://stahla.fly.dev/health
- **API Endpoints**: https://stahla.fly.dev/api/v1/

### MongoDB Connection

Internal connection string for the application:
```

mongodb://stahla_app:your_password@localhost:27017/stahla_dashboard

````

### Useful Commands

```bash
# Check application status
./manage-unified.sh status

# View all logs
./manage-unified.sh logs

# SSH into the machine
./manage-unified.sh ssh

# Check health
./manage-unified.sh health
````

### Direct Fly.io Commands

```bash
# Check application status
flyctl status --app stahla

# View logs
flyctl logs --app stahla

# SSH into the machine
flyctl ssh console --app stahla

# Scale the application
flyctl scale count 2 --app stahla
flyctl scale vm shared-cpu-2x --app stahla

# Update secrets
flyctl secrets set MONGO_PASSWORD=new_password --app stahla

# Deploy updates
flyctl deploy --app stahla
```

## Troubleshooting

### Service Startup Issues

1. **Check service status**:

   ```bash
   ./manage-unified.sh status
   ./manage-unified.sh logs
   ```

2. **SSH into the machine to debug**:

   ```bash
   ./manage-unified.sh ssh

   # Inside the machine, check processes
   ps aux | grep -E "(mongod|redis|uvicorn|nginx)"

   # Check service logs
   tail -f /data/logs/mongodb.log
   tail -f /data/logs/redis.log
   ```

### MongoDB Issues

1. **MongoDB won't start**:

   ```bash
   # Check logs
   tail -f /data/logs/mongodb.log

   # Check permissions
   ls -la /data/mongodb

   # Manual restart
   mongod --auth --bind_ip_all --dbpath /data/mongodb
   ```

2. **Authentication issues**:

   ```bash
   # Connect to MongoDB shell
   mongosh localhost:27017/stahla_dashboard

   # List users
   db.getUsers()
   ```

### API Issues

1. **FastAPI won't start**:

   ```bash
   # Check if all dependencies are installed
   pip list

   # Manual start for debugging
   cd /app && uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Database connection issues**:
   ```bash
   # Test MongoDB connection
   mongosh "mongodb://stahla_app:password@localhost:27017/stahla_dashboard"
   ```

### Nginx Issues

1. **502 Bad Gateway**: FastAPI service is down
2. **Configuration errors**:

   ```bash
   # Test Nginx config
   nginx -t

   # Reload configuration
   nginx -s reload
   ```

## Scaling and Production

### Scaling the Application

```bash
# Scale to multiple machines
flyctl scale count 2 --app stahla

# Upgrade VM size for better performance
flyctl scale vm shared-cpu-2x --app stahla
flyctl scale vm dedicated-cpu-2x --app stahla
```

### Monitoring

- Use Fly.io dashboard for metrics and logs
- Health check endpoint: `https://stahla.fly.dev/health`
- Monitor resource usage and scale accordingly

### Backups

```bash
# SSH into the machine
flyctl ssh console --app stahla

# Create MongoDB backup
mongodump --uri="mongodb://stahla_app:password@localhost:27017/stahla_dashboard" --out=/tmp/backup

# Exit and download backup
flyctl sftp get /tmp/backup ./backup --app stahla
```

## Security Considerations

1. **Strong passwords**: Use secure passwords for MongoDB
2. **Secrets management**: Store sensitive data as Fly.io secrets
3. **Regular updates**: Keep the application and dependencies updated
4. **Network security**: All internal communication via localhost
5. **HTTPS**: Automatic SSL/TLS via Fly.io

## Cost Optimization

- Start with `shared-cpu-1x` instances
- Scale up only when needed
- Monitor resource usage via Fly.io dashboard
- Use single-machine deployment for development
- Scale to multiple machines only for production

## Support

For issues with this deployment setup:

1. Check the logs: `./manage-unified.sh logs`
2. Verify service status: `./manage-unified.sh status`
3. SSH into the machine: `./manage-unified.sh ssh`
4. Check health endpoint: `./manage-unified.sh health`

For Fly.io specific issues, consult the [Fly.io documentation](https://fly.io/docs/).

## Summary

This unified deployment approach provides:

✅ **Single app deployment** (`stahla`) instead of multiple separate apps  
✅ **Simplified management** with unified scripts and commands  
✅ **Lower latency** between services (localhost communication)  
✅ **Reduced costs** with single machine instead of multiple instances  
✅ **Easier debugging** with all services in one place  
✅ **Automatic SSL** via Fly.io at `https://stahla.fly.dev`  
✅ **Persistent data** via mounted volume for MongoDB and Redis  
✅ **Health monitoring** with built-in health check endpoint

### Key Files for Deployment:

- `fly.toml` - Main application configuration
- `Dockerfile` - Unified container with all services
- `deploy-unified.sh` - One-command deployment
- `manage-unified.sh` - Application management
- `init.sh` - Service initialization

Ready to deploy! Run `./deploy-unified.sh` to get started.
