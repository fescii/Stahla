# 🚀 Stahla Deployment Checklist

Follow this checklist to successfully deploy your Stahla application to Fly.io.

## ✅ Pre-Deployment Checklist

### 1. Environment Setup

- [ ] Fly.io CLI installed (`curl -L https://fly.io/install.sh | sh`)
- [ ] Authenticated with Fly.io (`flyctl auth login`)
- [ ] In the correct directory (`cd /home/femar/AO3/Stahla/fly-deployment`)

### 2. Configuration Validation

```bash
# Run validation script
./validate.sh
```

- [ ] All configuration files present
- [ ] Application files accessible
- [ ] Scripts executable
- [ ] fly.toml configuration correct

### 3. Optional: Custom Configuration

- [ ] Review `fly.toml` - change app name if needed
- [ ] Check resource allocation (CPU/Memory)
- [ ] Verify region setting (`sjc` - San Jose)

## 🚀 Deployment Steps

### Step 1: Deploy the Application

```bash
./deploy-unified.sh
```

This will:

- ✅ Create the app if it doesn't exist
- ✅ Create persistent volume
- ✅ Build and deploy all services
- ✅ Initialize MongoDB and Redis
- ✅ Start all services

### Step 2: Verify Deployment

```bash
# Check application status
./manage-unified.sh status

# View deployment logs
./manage-unified.sh logs

# Test health endpoint
curl https://stahla.fly.dev/health
```

### Step 3: Access Your Application

- [ ] Open https://stahla.fly.dev
- [ ] Verify API endpoints work
- [ ] Check that static files load correctly

## 📊 Post-Deployment Verification

### Health Checks

- [ ] Application responds at https://stahla.fly.dev
- [ ] Health endpoint returns 200: https://stahla.fly.dev/health
- [ ] API endpoints accessible: https://stahla.fly.dev/api/v1/
- [ ] Static files loading: https://stahla.fly.dev/static/

### Service Status

```bash
# SSH into the machine
./manage-unified.sh ssh

# Check all services are running
ps aux | grep -E "(mongod|redis|uvicorn|nginx)"

# Check service logs
tail -f /data/logs/mongodb.log
tail -f /data/logs/redis.log
```

### Database Verification

```bash
# Connect to MongoDB (from inside the machine)
mongosh localhost:27017/stahla_dashboard

# Test Redis connection
redis-cli ping
```

## 🔧 Common Management Tasks

### Monitoring

```bash
# View real-time logs
./manage-unified.sh logs

# Check application status
./manage-unified.sh status

# Monitor resource usage
flyctl status --app stahla
```

### Scaling

```bash
# Scale to multiple instances
flyctl scale count 2 --app stahla

# Upgrade VM size
flyctl scale vm shared-cpu-2x --app stahla
```

### Updates

```bash
# Redeploy after code changes
./deploy-unified.sh

# Restart without redeploying
./manage-unified.sh restart
```

## 🆘 Troubleshooting

### If Deployment Fails

1. Check the error message carefully
2. Run `./validate.sh` to verify configuration
3. Check `TROUBLESHOOTING.md` for common issues
4. View logs: `./manage-unified.sh logs`

### If Services Won't Start

```bash
# SSH into the machine
./manage-unified.sh ssh

# Check what's running
ps aux | grep -E "(mongod|redis|uvicorn|nginx)"

# Check service logs
tail -f /data/logs/*.log

# Restart services manually if needed
/app/init.sh --supervisor
```

### Get Help

- Review `README.md` for detailed documentation
- Check `TROUBLESHOOTING.md` for specific issues
- Use `./manage-unified.sh help` for management commands
- Fly.io docs: https://fly.io/docs/

## 🎉 Success Criteria

Your deployment is successful when:

- [ ] https://stahla.fly.dev loads without errors
- [ ] Health check returns 200 OK
- [ ] All services show as running in logs
- [ ] Database connections work
- [ ] Static files are served correctly

## 📝 Next Steps

After successful deployment:

1. Set up monitoring and alerts
2. Configure backup procedures
3. Set up CI/CD for automated deployments
4. Consider scaling based on usage
5. Review security settings

---

**Ready to deploy?** Run `./deploy-unified.sh` and watch your application come to life! 🚀
