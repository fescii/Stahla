# 📋 Stahla Quick Reference

## Essential Commands

### 🚀 Deploy

```bash
./deploy-unified.sh          # Full deployment
```

### 📊 Monitor

```bash
./manage-unified.sh status   # App status
./manage-unified.sh logs     # View logs
./manage-unified.sh health   # Health check
```

### 🔧 Manage

```bash
./manage-unified.sh ssh      # SSH into machine
./manage-unified.sh restart  # Restart app
./manage-unified.sh info     # Detailed info
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
fly-deployment/
├── fly.toml                 # Main config
├── Dockerfile               # Multi-service container
├── deploy-unified.sh        # Deployment script
├── manage-unified.sh        # Management script
├── init.sh     # Service initialization
├── validate.sh              # Validation script
├── README.md                # Full documentation
├── TROUBLESHOOTING.md       # Problem solving
└── old-individual-services/ # Backup configs
```

## Emergency Commands

### Restart Everything

```bash
flyctl apps restart stahla
```

### View All Processes

```bash
./manage-unified.sh ssh
ps aux | grep -E "(mongod|redis|uvicorn|nginx)"
```

### Nuclear Option (Destroys Everything!)

```bash
flyctl apps destroy stahla  # ⚠️ BE VERY CAREFUL!
./deploy-unified.sh         # Redeploy from scratch
```

## Getting Help

```bash
./manage-unified.sh help     # Management commands
flyctl help                  # Fly.io commands
```

---

**Need more details?** Check `README.md` or `TROUBLESHOOTING.md`
