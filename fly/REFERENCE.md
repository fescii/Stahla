# 📋 Stahla Quick Reference

## Essential Commands

### 🚀 Deploy

```bash
./deploy.sh          # Full deployment
```

### 📊 Monitor

```bash
./manage.sh status   # App status
./manage.sh logs     # View logs
./manage.sh health   # Health check
```

### 🔧 Manage

```bash
./manage.sh ssh      # SSH into machine
./manage.sh restart  # Restart app
./manage.sh info     # Detailed info
```

### 🔍 Debug

```bash
./validate.sh               # Validate config
flyctl logs --app stahla    # Fly.io logs
flyctl status --app stahla  # Fly.io status
```

## Quick URLs

- **App**: https://stahla.fly.dev
- **Health**: https://stahla.fly.dev/health
- **API**: https://stahla.fly.dev/api/v1/

## Service Ports (Internal)

- **Nginx**: 80/443 (external)
- **FastAPI**: 8000 (localhost)
- **MongoDB**: 27017 (localhost)
- **Redis**: 6379 (localhost)

## File Structure

```
fly/
├── fly.toml                 # Main config
├── Dockerfile               # Multi-service container (referenced from parent directory)
├── deploy.sh                # Deployment script
├── manage.sh                # Management script
├── init.sh                  # Service initialization
├── startup.sh               # Release command script 
├── validate.sh              # Validation script
├── README.md                # Full documentation
├── TROUBLESHOOT.md          # Problem solving
└── api/                     # Subdirectories with old configs
    mongodb/
    nginx/
    redis/
```

## Emergency Commands

### Restart Everything

```bash
flyctl apps restart stahla
```

### View All Processes

```bash
./manage.sh ssh
ps aux | grep -E "(mongod|redis|uvicorn|nginx)"
```

### Nuclear Option (Destroys Everything!)

```bash
flyctl apps destroy stahla  # ⚠️ BE VERY CAREFUL!
./deploy.sh                 # Redeploy from scratch
```

## Getting Help

```bash
./manage.sh help     # Management commands
flyctl help          # Fly.io commands
```

---

**Need more details?** Check `README.md` or `TROUBLESHOOTING.md`
