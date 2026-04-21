# Artio Mine Bot — Docker VM Deployment Guide

**Target:** craig@dockerdev (Docker development VM)  
**Method:** Automated deployment via SSH  
**Time:** ~10-15 minutes (including 3-5 min Docker build)

---

## Quick Start (TL;DR)

```bash
# 1. Get your OpenAI API key from https://platform.openai.com/api-keys
# 2. Run the deployment script:
./deploy.sh sk-proj-YOUR_KEY_HERE craig@dockerdev 8000

# 3. Wait for completion (will show success message with access URLs)
# 4. Open browser to http://craig@dockerdev:5173
```

---

## Prerequisites

### Local Machine (Your Computer)

- [ ] SSH configured with key-based authentication
- [ ] Ability to SSH to craig@dockerdev without password
  ```bash
  # Test: should work without prompting for password
  ssh craig@dockerdev "echo connected"
  ```

### Remote Machine (craig@dockerdev)

- [ ] Docker installed
  ```bash
  ssh craig@dockerdev "docker --version"
  ```
- [ ] Docker Compose installed
  ```bash
  ssh craig@dockerdev "docker-compose --version"
  ```
- [ ] ~50GB free disk space (for Docker images and data)
- [ ] git installed
  ```bash
  ssh craig@dockerdev "git --version"
  ```

#### If Docker/Compose Not Installed

```bash
# SSH to remote machine
ssh craig@dockerdev

# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group (no sudo needed)
sudo usermod -aG docker craig

# Log out and back in for group changes to take effect
exit
ssh craig@dockerdev

# Verify
docker --version
docker-compose --version
```

---

## Step-by-Step Deployment

### Step 1: Get Your OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new API key (or copy existing)
3. Save somewhere safe (format: `sk-proj-...`)

### Step 2: Verify SSH Access

```bash
# Should return "connected" without password prompt
ssh -o BatchMode=yes craig@dockerdev "echo connected"

# If you get a prompt for password:
# • You need to set up SSH key-based auth
# • See "SSH Setup" section below
```

### Step 3: Run Deployment Script

```bash
# Navigate to where you have the deployment script
cd ~/Downloads  # or wherever you saved deploy.sh

# Make executable if not already
chmod +x deploy.sh

# Run with your API key
./deploy.sh sk-proj-YOUR_ACTUAL_KEY craig@dockerdev 8000

# Example with real key:
./deploy.sh sk-proj-abc123def456xyz craig@dockerdev 8000
```

### Step 4: Monitor Deployment

The script will output colored status messages:

```
✅ SSH connectivity verified
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Deploying Artio Mine Bot to craig@dockerdev
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/6] Preparing remote directory...
  Repository ready at /home/craig/artio-mine-bot
✅ Remote directory prepared

[2/6] Creating .env configuration...
✅ Configuration file created

[3/6] Verifying Docker installation...
Docker version 24.0.0, build abc123
Docker Compose version 2.20.0
✅ Docker verified

[4/6] Building Docker images...
  This may take 3-5 minutes on first build...
  Building backend image...
  [numerous build steps...]
  Building frontend image...
  [numerous build steps...]
✅ Docker images built

[5/6] Starting containers...
  Waiting for services to start...
  Attempt 1/10: Waiting for API to start...
  ✅ API is healthy
  NAME             COMMAND                  SERVICE      STATUS
  artio-api        ./start.sh               api          Up 2 seconds
  artio-frontend   nginx -g daemon off;     frontend     Up 1 second
✅ Containers started

[6/6] Running health checks...
  Testing API health...
  ✅ API responding
  Testing database connectivity...
  ✅ Database initialized
  [container status table]
✅ Health checks complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DEPLOYMENT SUCCESSFUL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Access your application:

  🌐 Frontend: http://craig@dockerdev:5173
  🔌 API: http://craig@dockerdev:8000
  💚 Health: http://craig@dockerdev:8000/health

[useful commands...]
```

### Step 5: Verify Access

```bash
# Test API health
curl http://craig@dockerdev:8000/health

# Should return:
# {
#   "status": "ok",
#   "version": "1.0.0",
#   "db": "ok",
#   "openai": "configured"
# }
```

### Step 6: Access the Application

Open in your browser:
- **Frontend:** http://craig@dockerdev:5173
- **API:** http://craig@dockerdev:8000
- **API Docs:** http://craig@dockerdev:8000/docs

---

## Post-Deployment

### Verify Everything Works

1. **Open Frontend** → http://craig@dockerdev:5173
2. **Add a Test Source** → Click "Add Source"
3. **Enter URL** → e.g., `https://www.example.com`
4. **Start Mining** → Click "Start Mining"
5. **Check Results** → Should see pages and records added

### Check Logs in Real-Time

```bash
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -f'

# Watch specific service:
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -f api'
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -f frontend'

# Exit with Ctrl+C
```

### Access Database

```bash
# View database tables
ssh craig@dockerdev \
  'docker-compose exec api sqlite3 /app/data/miner.db ".tables"'

# Run SQL query
ssh craig@dockerdev \
  'docker-compose exec api sqlite3 /app/data/miner.db "SELECT COUNT(*) FROM records;"'
```

### Restart Services (if needed)

```bash
# Restart all containers
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose restart'

# Restart only API
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose restart api'

# Full stop and start
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose down && docker-compose up -d'
```

### Stop Services

```bash
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose down'
```

---

## Configuration Management

### Environment Variables

Configuration is stored in `/home/craig/artio-mine-bot/.env`:

```bash
# View current config
ssh craig@dockerdev 'cat artio-mine-bot/.env'

# Edit config (nano editor)
ssh craig@dockerdev 'nano artio-mine-bot/.env'

# After editing, restart services:
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose down && docker-compose up -d'
```

### Important Settings

| Variable | Current | Can Change? | Impact |
|----------|---------|-------------|--------|
| `OPENAI_API_KEY` | Set during deploy | ✅ Yes | Required for AI extraction |
| `OPENAI_MODEL` | gpt-4o | ✅ Yes | Model used for extraction |
| `DATABASE_URL` | SQLite | ⚠️ Careful | Switch to PostgreSQL for production |
| `MAX_CRAWL_DEPTH` | 3 | ✅ Yes | How deep to crawl from start URL |
| `MAX_PAGES_PER_SOURCE` | 500 | ✅ Yes | Limit pages per source |
| `CRAWL_DELAY_MS` | 1000 | ✅ Yes | Delay between requests (be respectful!) |
| `PLAYWRIGHT_ENABLED` | true | ✅ Yes | Enable JavaScript rendering |
| `CORS_ORIGINS` | localhost | ✅ Yes | Allow requests from other origins |

### Making Changes

```bash
# Edit .env
ssh craig@dockerdev 'nano artio-mine-bot/.env'

# Restart to apply changes
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose restart api'

# Verify
curl http://craig@dockerdev:8000/health
```

---

## Troubleshooting

### Issue: "Cannot connect to ssh host"

**Cause:** SSH key not configured or not authorized on remote

**Solution:**
```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519

# Add your public key to remote
ssh-copy-id -i ~/.ssh/id_ed25519.pub craig@dockerdev

# Test
ssh craig@dockerdev "echo connected"
```

### Issue: "Docker not found"

**Cause:** Docker not installed on remote machine

**Solution:**
```bash
ssh craig@dockerdev << 'EOF'
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker craig
EOF
```

Then log out and back in for group changes to take effect.

### Issue: "Cannot build Docker images" / "Build timeout"

**Cause:** First build takes 3-5 minutes (Playwright browser installation)

**Solution:**
- Be patient, allow 5-10 minutes for first deployment
- Check logs: `ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs api'`
- For subsequent deployments, caching makes it much faster

### Issue: API returns "openai: not configured"

**Cause:** `OPENAI_API_KEY` not set in .env

**Solution:**
```bash
# Edit .env
ssh craig@dockerdev 'nano artio-mine-bot/.env'

# Find line with OPENAI_API_KEY and set it:
# OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY

# Save (Ctrl+O, Enter, Ctrl+X in nano)

# Restart API
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose restart api'

# Verify
curl http://craig@dockerdev:8000/health
```

### Issue: Port 8000 or 5173 already in use

**Cause:** Another application using those ports

**Solution:**
```bash
# Check what's using the ports
ssh craig@dockerdev 'netstat -tlnp | grep 8000'

# Option 1: Stop the other application
ssh craig@dockerdev 'sudo systemctl stop other-service'

# Option 2: Use different port in docker-compose.yml
ssh craig@dockerdev 'cd artio-mine-bot && nano docker-compose.yml'
# Change: "8000:8000" to "8001:8000"
# Change: "5173:80" to "5174:80"
# Restart:
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose down && docker-compose up -d'
```

### Issue: Disk space full

**Cause:** Docker images and data consuming too much space

**Solution:**
```bash
# Check space
ssh craig@dockerdev 'df -h'

# Clean up unused Docker objects
ssh craig@dockerdev 'docker system prune -a'

# If still full, check data volume size
ssh craig@dockerdev 'docker volume ls'
ssh craig@dockerdev 'docker volume inspect artio-mine-bot_artio_data'
```

### Issue: Can't access frontend/API from other machines

**Cause:** Firewall blocking ports 8000/5173

**Solution:**
```bash
# Open ports in firewall
ssh craig@dockerdev << 'EOF'
sudo ufw allow 8000/tcp
sudo ufw allow 5173/tcp
sudo ufw reload
EOF

# Or: Access via SSH tunnel
ssh -L 8000:localhost:8000 -L 5173:localhost:5173 craig@dockerdev
# Then open browser to http://localhost:8000
```

---

## Data Backup & Recovery

### Backup Database

```bash
ssh craig@dockerdev 'docker-compose exec api sqlite3 /app/data/miner.db ".dump" > /tmp/artio_backup.sql'

# Or use tar to backup entire data volume
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose exec -T api tar czf - /app/data > /tmp/artio_data_backup.tar.gz'
```

### Restore from Backup

```bash
# Restore to new container
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose exec api sqlite3 /app/data/miner.db < /tmp/artio_backup.sql'
```

### Full Volume Backup (to local machine)

```bash
# Backup
scp craig@dockerdev:/tmp/artio_data_backup.tar.gz ~/backups/

# Restore (if needed)
scp ~/backups/artio_data_backup.tar.gz craig@dockerdev:/tmp/
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose down && \
  docker volume rm artio-mine-bot_artio_data && \
  docker volume create artio-mine-bot_artio_data && \
  docker-compose up -d'
```

---

## Performance Monitoring

### View Container Stats

```bash
# Real-time CPU/Memory usage
ssh craig@dockerdev 'docker stats --no-stream'

# Watch continuous
ssh craig@dockerdev 'watch docker stats --no-stream'
```

### Check Logs for Performance Issues

```bash
# View last 100 lines
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -n 100 api'

# Follow in real-time
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -f api'

# Search for errors
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs api | grep -i error'

# Search for slow queries
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs api | grep -i "slow"'
```

---

## Updating the Application

### Pull Latest Changes

```bash
ssh craig@dockerdev 'cd artio-mine-bot && git pull origin main'
```

### Rebuild and Redeploy

```bash
ssh craig@dockerdev << 'EOF'
cd artio-mine-bot

# Stop current
docker-compose down

# Pull latest
git pull origin main

# Rebuild (only rebuilds changed layers)
docker-compose build --no-cache

# Start
docker-compose up -d

# Verify
curl http://localhost:8000/health
EOF
```

---

## Useful Commands Reference

| Task | Command |
|------|---------|
| **View logs** | `ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -f'` |
| **Stop services** | `ssh craig@dockerdev 'cd artio-mine-bot && docker-compose down'` |
| **Start services** | `ssh craig@dockerdev 'cd artio-mine-bot && docker-compose up -d'` |
| **Restart services** | `ssh craig@dockerdev 'cd artio-mine-bot && docker-compose restart'` |
| **Shell access** | `ssh craig@dockerdev 'cd artio-mine-bot && docker-compose exec api /bin/bash'` |
| **Check health** | `curl http://craig@dockerdev:8000/health` |
| **Database query** | `ssh craig@dockerdev 'docker-compose exec api sqlite3 /app/data/miner.db "SQL_QUERY"'` |
| **View config** | `ssh craig@dockerdev 'cat artio-mine-bot/.env'` |
| **Edit config** | `ssh craig@dockerdev 'nano artio-mine-bot/.env'` |
| **Upgrade DB** | `ssh craig@dockerdev 'cd artio-mine-bot && docker-compose exec api alembic upgrade head'` |

---

## Next Steps

1. ✅ Deployment complete
2. 📝 Create test sources and run mining jobs
3. 📊 Review mined data in dashboard
4. 🔧 Adjust crawl settings based on your needs
5. 🔐 Configure production authentication (`X-Admin-Token` and/or `X-API-Key`); development auto-admin is not allowed in production
6. 📈 Set up monitoring and logging aggregation
7. 🌐 If public-facing, add SSL/TLS certificate

---

## Support

If you encounter issues:

1. Check logs: `ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -f'`
2. Review troubleshooting section above
3. Verify SSH connectivity and permissions
4. Check if Docker/Docker Compose are running
5. Ensure adequate disk space (min 50GB)

For API documentation: http://craig@dockerdev:8000/docs
For deployment script help: `./deploy.sh --help` (or just run without args for usage)
