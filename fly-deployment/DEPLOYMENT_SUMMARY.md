# Stahla Unified Fly.io Deployment - Configuration Complete

## ✅ What We've Accomplished

### 1. **Single Unified App Configuration**

- Converted from multiple separate Fly.io apps to one unified app: `stahla`
- All services (MongoDB, Redis, FastAPI, Nginx) run in the same container
- Communication via localhost for better performance and lower costs

### 2. **Complete File Structure Created**

```
fly-deployment/
├── fly.toml                    # Main Fly.io app configuration
├── Dockerfile                  # Unified container with all services
├── init-all-services.sh        # Service initialization script
├── deploy-unified.sh          # One-command deployment script
├── manage-unified.sh          # Application management script
├── validate.sh                # Pre-deployment validation
├── README.md                  # Complete documentation
└── old-individual-services/   # Backup of original configs
    ├── api/
    ├── mongodb/
    ├── nginx/
    └── redis/
```

### 3. **Key Configuration Details**

#### App Configuration (`fly.toml`):

- **App Name**: `stahla`
- **Region**: `sjc` (San Jose)
- **Domain**: `https://stahla.fly.dev`
- **Volume**: `stahla_data` for persistent storage
- **VM Size**: 2 CPUs, 2GB RAM
- **Process**: Single supervisor process managing all services

#### Services:

- **MongoDB**: Port 27017 (localhost), authenticated, persistent data
- **Redis**: Port 6379 (localhost), with persistence
- **FastAPI**: Port 8000 (localhost), Python application
- **Nginx**: Port 80/443 (external), reverse proxy + static files

#### Environment Variables:

- `MONGO_HOST=localhost`
- `REDIS_URL=redis://localhost:6379/0`
- All services use localhost for internal communication

### 4. **Deployment Process**

1. **Validate**: `./validate.sh` - Check configuration
2. **Deploy**: `./deploy-unified.sh` - One-command deployment
3. **Manage**: `./manage-unified.sh` - Status, logs, health checks

### 5. **Benefits of Unified Approach**

✅ **Simplified Management**: One app instead of four  
✅ **Lower Costs**: Single machine vs multiple instances  
✅ **Faster Communication**: localhost vs network calls  
✅ **Easier Debugging**: All services in one place  
✅ **Single Domain**: https://stahla.fly.dev for everything  
✅ **Automatic SSL**: Handled by Fly.io

## 🚀 Ready to Deploy!

### Prerequisites

1. Install Fly.io CLI: `curl -L https://fly.io/install.sh | sh`
2. Login to Fly.io: `flyctl auth login`
3. Run validation: `./validate.sh`

### Deploy Command

```bash
cd /home/femar/AO3/Stahla/fly-deployment
./deploy-unified.sh
```

This will automatically:

1. **Create the app** if it doesn't exist
2. **Create the volume** for persistent data
3. **Build and deploy** all services
4. **Initialize** MongoDB and Redis
5. **Start** all services (MongoDB, Redis, FastAPI, Nginx)

### Post-Deployment

- **Application URL**: https://stahla.fly.dev
- **Health Check**: https://stahla.fly.dev/health
- **Management**: `./manage-unified.sh status`

## 📋 Quick Reference

### Deployment Commands

```bash
./deploy-unified.sh           # Deploy application
./manage-unified.sh status    # Check status
./manage-unified.sh logs      # View logs
./manage-unified.sh ssh       # SSH into machine
./manage-unified.sh health    # Check health
```

### Fly.io Commands

```bash
flyctl status --app stahla         # Check status
flyctl logs --app stahla           # View logs
flyctl ssh console --app stahla    # SSH access
flyctl scale count 2 --app stahla  # Scale to 2 instances
```

## 🔧 Configuration Files Summary

| File                   | Purpose                            |
| ---------------------- | ---------------------------------- |
| `fly.toml`             | Main Fly.io configuration          |
| `Dockerfile`           | Multi-service container definition |
| `init-all-services.sh` | Service startup and initialization |
| `deploy-unified.sh`    | Deployment automation              |
| `manage-unified.sh`    | Operations management              |
| `validate.sh`          | Pre-deployment validation          |

The deployment is now ready for a single Fly.io app that will run all services efficiently at `https://stahla.fly.dev`!
