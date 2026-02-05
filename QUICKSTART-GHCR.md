# Quick Start with Published Docker Images

Use pre-built Docker images from GitHub Container Registry for the fastest setup!

## Prerequisites

- Docker Desktop installed and running
- Internet connection to pull images

## Method 1: Docker Compose (Recommended)

**Step 1: Pull the compose file**
```bash
# Use the GHCR-specific compose file
docker-compose -f docker-compose.ghcr.yml pull
```

**Step 2: Start services**
```bash
docker-compose -f docker-compose.ghcr.yml up -d
```

**Step 3: Access the app**
Open your browser to: **http://localhost:8000**

**Stop services:**
```bash
docker-compose -f docker-compose.ghcr.yml down
```

---

## Method 2: Standalone Docker Run

**Pull and run in one command:**
```bash
docker run -d \
  --name notetime \
  -p 8000:8000 \
  ghcr.io/pinhead001/notetime:latest
```

**Stop:**
```bash
docker stop notetime
docker rm notetime
```

---

## Method 3: Windows (Command Prompt)

**Step 1: Navigate to notetime folder**
```cmd
cd C:\path\to\notetime
```

**Step 2: Pull and start**
```cmd
docker-compose -f docker-compose.ghcr.yml up -d
```

**Step 3: Open browser**
http://localhost:8000

**Stop:**
```cmd
docker-compose -f docker-compose.ghcr.yml down
```

---

## Using Specific Versions

**Pull a specific version:**
```bash
docker pull ghcr.io/pinhead001/notetime:1.0.0
```

**Run specific version:**
```bash
docker run -d -p 8000:8000 ghcr.io/pinhead001/notetime:1.0.0
```

**Or edit docker-compose.ghcr.yml:**
```yaml
web:
  image: ghcr.io/pinhead001/notetime:1.0.0  # Pin to specific version
```

---

## Available Tags

- `latest` - Most recent build from main branch
- `1.0.0`, `1.0`, `1` - Semantic version tags
- `main-<sha>` - Specific commit builds

**View all available tags:**
https://github.com/pinhead001/notetime/pkgs/container/notetime

---

## Advantages of Using Published Images

✅ **No build time** - Images are pre-built (saves 3-5 minutes)
✅ **Consistent** - Same image for development and production
✅ **Tested** - Automatically built and tested by CI/CD
✅ **Cached** - Docker pulls are fast with layer caching
✅ **Versioned** - Pin to specific versions for stability

---

## Updating to Latest Version

```bash
# Pull latest image
docker-compose -f docker-compose.ghcr.yml pull

# Restart services with new image
docker-compose -f docker-compose.ghcr.yml up -d
```

---

## With Database Persistence

Using `docker-compose.ghcr.yml` automatically includes PostgreSQL with persistent storage.

**To reset database:**
```bash
docker-compose -f docker-compose.ghcr.yml down -v
docker-compose -f docker-compose.ghcr.yml up -d
```

**⚠️ Warning:** This deletes all data!

---

## Troubleshooting

### Can't Pull Image (403 Forbidden)

**If the image is private, authenticate first:**

```bash
# Create a GitHub Personal Access Token with 'read:packages' scope
# Then login:
echo YOUR_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Now pull:
docker pull ghcr.io/pinhead001/notetime:latest
```

### Image Not Found

**Make sure the image has been published:**
1. Check: https://github.com/pinhead001/notetime/actions
2. Verify latest workflow completed successfully
3. Check: https://github.com/pinhead001/notetime/pkgs/container/notetime

### Port 8000 Already in Use

**Use a different port:**
```bash
docker run -d -p 8001:8000 ghcr.io/pinhead001/notetime:latest
# Access at http://localhost:8001
```

---

## Production Deployment

**Recommended for production:**

```yaml
# docker-compose.prod.yml
services:
  web:
    image: ghcr.io/pinhead001/notetime:1.0.0  # Pin to version
    restart: unless-stopped
    environment:
      DATABASE_URL: ${DATABASE_URL}
      ENVIRONMENT: production
```

**Deploy:**
```bash
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

---

## Next Steps

- See [GITHUB-ACTIONS.md](GITHUB-ACTIONS.md) for CI/CD details
- See [DOCKER.md](DOCKER.md) for complete Docker documentation
- See [README.md](README.md) for general information

---

## Quick Commands Reference

```bash
# Pull latest
docker pull ghcr.io/pinhead001/notetime:latest

# Run with compose
docker-compose -f docker-compose.ghcr.yml up -d

# Run standalone
docker run -d -p 8000:8000 ghcr.io/pinhead001/notetime:latest

# Update to latest
docker-compose -f docker-compose.ghcr.yml pull
docker-compose -f docker-compose.ghcr.yml up -d

# Stop
docker-compose -f docker-compose.ghcr.yml down

# View logs
docker logs notetime-app -f
```

That's it! You're running Notetime with published images! 🚀
