# Artio Mine Bot — Quick Deployment (5 Minutes)

## Prerequisites ✅

Before starting, make sure you have:

- [ ] OpenAI API key (get from https://platform.openai.com/api-keys)
- [ ] SSH access to craig@dockerdev
- [ ] Can SSH without password prompt:
  ```bash
  ssh -o BatchMode=yes craig@dockerdev "echo connected"
  ```

---

## One-Command Deployment

```bash
./deploy.sh sk-proj-YOUR_API_KEY craig@dockerdev 8000
```

**Replace `sk-proj-YOUR_API_KEY` with your actual OpenAI API key**

Example:
```bash
./deploy.sh sk-proj-abc123xyz789 craig@dockerdev 8000
```

---

## What This Does (Automatically)

1. ✅ Verifies SSH connectivity
2. ✅ Clones GitHub repository to `/home/craig/artio-mine-bot`
3. ✅ Creates `.env` configuration file with your API key
4. ✅ Verifies Docker/Docker Compose installed
5. ✅ Builds Docker images (3-5 minutes first time)
6. ✅ Starts containers
7. ✅ Initializes database
8. ✅ Runs health checks
9. ✅ Displays access URLs

---

## Expected Output

```
✅ SSH connectivity verified
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Deploying Artio Mine Bot to craig@dockerdev
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/6] Preparing remote directory...
✅ Remote directory prepared

[2/6] Creating .env configuration...
✅ Configuration file created

[3/6] Verifying Docker installation...
✅ Docker verified

[4/6] Building Docker images...
  This may take 3-5 minutes on first build...
✅ Docker images built

[5/6] Starting containers...
✅ Containers started

[6/6] Running health checks...
✅ Health checks complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DEPLOYMENT SUCCESSFUL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 Frontend: http://craig@dockerdev:5173
🔌 API: http://craig@dockerdev:8000
💚 Health: http://craig@dockerdev:8000/health
```

---

## Access Your Application

### Via Web Browser
- **Frontend:** http://craig@dockerdev:5173
- **API Docs:** http://craig@dockerdev:8000/docs

### Via Command Line

```bash
# Test API health
curl http://craig@dockerdev:8000/health

# View logs
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -f'

# Access database
ssh craig@dockerdev 'docker-compose exec api sqlite3 /app/data/miner.db ".tables"'
```

---

## Common Tasks

### Stop Services
```bash
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose down'
```

### Start Services Again
```bash
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose up -d'
```

### View Logs
```bash
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose logs -f'
```

### Restart Services
```bash
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose restart'
```

### Update Configuration
```bash
ssh craig@dockerdev 'nano artio-mine-bot/.env'
# Edit, then save and exit
ssh craig@dockerdev 'cd artio-mine-bot && docker-compose restart api'
```

---

## Troubleshooting

### "Cannot connect to ssh host"
Make sure you can SSH without a password prompt:
```bash
ssh -o BatchMode=yes craig@dockerdev "echo connected"
```

If this fails, you need to set up SSH key authentication:
```bash
# Generate key (if needed)
ssh-keygen -t ed25519

# Add to remote
ssh-copy-id -i ~/.ssh/id_ed25519.pub craig@dockerdev

# Test
ssh -o BatchMode=yes craig@dockerdev "echo connected"
```

### "Docker not found"
Docker not installed on remote. SSH to remote and install:
```bash
ssh craig@dockerdev
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker craig
exit
```

### "Build timeout" or "Build takes long"
This is normal for first build (Playwright browser installation takes 3-5 minutes).
Just wait. Subsequent deployments will be much faster.

### "Cannot access http://craig@dockerdev:5173"
Check firewall:
```bash
ssh craig@dockerdev 'sudo ufw allow 8000/tcp && sudo ufw allow 5173/tcp'
```

Or use SSH tunneling:
```bash
ssh -L 8000:localhost:8000 -L 5173:localhost:5173 craig@dockerdev
# Then open http://localhost:5173 in your browser
```

---

## Next Steps

1. ✅ Run deployment script
2. 📝 Open frontend at http://craig@dockerdev:5173
3. ➕ Add a test source (enter a URL)
4. 🔨 Start mining to test
5. 📊 Review results in dashboard
6. 🔧 Adjust settings as needed

---

## Full Documentation

For detailed instructions, configuration options, and advanced topics, see:
- `DEPLOYMENT_GUIDE.md` — Comprehensive deployment guide
- `DOCKER_DEPLOYMENT_ANALYSIS.md` — Technical analysis and architecture
- `AUDIT_REPORT.md` — Code quality and architecture audit

---

## Script Usage

```bash
# Show help (run without arguments)
./deploy.sh

# Full usage
./deploy.sh <openai-api-key> [ssh-host] [port]

# Examples
./deploy.sh sk-proj-abc123 craig@dockerdev 8000
./deploy.sh sk-proj-abc123 user@192.168.1.100 9000
./deploy.sh sk-proj-abc123  # Uses default craig@dockerdev:8000
```

---

**Ready? Let's deploy!**

```bash
./deploy.sh sk-proj-YOUR_API_KEY craig@dockerdev 8000
```
