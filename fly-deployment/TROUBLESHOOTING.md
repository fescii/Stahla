# Quick Deployment Troubleshooting Guide

## Common Issues and Solutions

### 1. **App Name Already Taken**

```
Error: App name 'stahla' is not available
```

**Solution**: Edit `fly.toml` and change the app name:

```toml
app = "stahla-yourname"  # or another unique name
```

### 2. **Authentication Issues**

```
Error: Not authenticated
```

**Solution**: Login to Fly.io:

```bash
flyctl auth login
```

### 3. **Volume Creation Fails**

```
Error: failed to create volume
```

**Solution**: Check if you have quota or try a different region:

```bash
flyctl volumes create stahla_data --size 10 --region ord --app stahla
```

### 4. **Build Failures**

```
Error: failed to build
```

**Solutions**:

- Check Dockerfile syntax: Run `validate.sh`
- Ensure all referenced files exist
- Check Docker build logs for specific errors

### 5. **Service Won't Start**

```
Error: health check failed
```

**Solutions**:

```bash
# Check logs
./manage-unified.sh logs

# SSH into machine to debug
./manage-unified.sh ssh

# Check individual services
ps aux | grep -E "(mongod|redis|uvicorn|nginx)"
```

### 6. **MongoDB Connection Issues**

```
Error: Authentication failed
```

**Solutions**:

```bash
# SSH into machine
./manage-unified.sh ssh

# Check MongoDB status
systemctl status mongod

# Test MongoDB connection
mongosh localhost:27017/stahla_dashboard
```

### 7. **Port Conflicts**

```
Error: bind: address already in use
```

**Solution**: This shouldn't happen in the unified setup, but if it does:

```bash
# Check what's using the port
netstat -tulpn | grep :8000
```

### 8. **Resource Limits**

```
Error: out of memory
```

**Solution**: Scale up the VM:

```bash
flyctl scale vm shared-cpu-2x --app stahla
```

## Quick Recovery Commands

### Restart Everything

```bash
flyctl apps restart stahla
```

### Redeploy

```bash
./deploy-unified.sh
```

### Check Status

```bash
./manage-unified.sh status
./manage-unified.sh health
```

### Get Help

```bash
./manage-unified.sh help
flyctl help
```

## Emergency Reset

If everything is broken and you want to start fresh:

```bash
# WARNING: This will destroy all data!
flyctl apps destroy stahla
./deploy-unified.sh  # Redeploy from scratch
```

## Contact Support

- **Fly.io Support**: https://fly.io/docs/
- **GitHub Issues**: Create an issue with your logs
- **Discord**: Fly.io community Discord
