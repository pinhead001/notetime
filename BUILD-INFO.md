# Checking Docker Image Build Information

This guide explains how to check which branch/commit a Docker image was built from.

## Quick Check Methods

### Method 1: Check Version API Endpoint

The easiest way - just visit the version endpoint:

**In browser:**
```
http://localhost:8000/version
```

**Or with curl:**
```bash
curl http://localhost:8000/version
```

**Response:**
```json
{
  "version": "1.0.0",
  "git_branch": "main",
  "git_commit": "2e39a8c1234567890abcdef",
  "build_date": "2024-02-04T12:34:56Z",
  "environment": "production"
}
```

---

### Method 2: Inspect Docker Image Labels

Check the image metadata:

```bash
# Inspect running container
docker inspect notetime-app --format='{{.Config.Labels}}'

# Or inspect the image directly
docker inspect notetime:latest --format='{{json .Config.Labels}}' | jq
```

**Example output:**
```json
{
  "git.branch": "main",
  "git.commit": "2e39a8c",
  "build.date": "2024-02-04T12:34:56Z"
}
```

---

### Method 3: Check Container Environment Variables

```bash
# View all environment variables
docker exec notetime-app env | grep GIT

# Or specific variables
docker exec notetime-app printenv GIT_BRANCH
docker exec notetime-app printenv GIT_COMMIT
```

---

## Building with Branch Info

### Local Build (Docker Compose)

When building locally, pass git info as environment variables:

```bash
# On Windows PowerShell
$env:GIT_BRANCH = git rev-parse --abbrev-ref HEAD
$env:GIT_COMMIT = git rev-parse --short HEAD
docker-compose up --build

# On Linux/Mac
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
export GIT_COMMIT=$(git rev-parse --short HEAD)
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
docker-compose up --build
```

### Manual Docker Build

```bash
docker build \
  --build-arg GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD) \
  --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  -t notetime:latest .
```

---

## GitHub Actions (Automatic)

When images are built by GitHub Actions, build info is automatically added:

**On push to main:**
- `git_branch`: "main"
- `git_commit`: Full commit SHA
- `build_date`: Commit timestamp

**On version tag (v1.0.0):**
- Same as above
- Plus version tags

**Check published image:**
```bash
# Pull from GHCR
docker pull ghcr.io/pinhead001/notetime:latest

# Check labels
docker inspect ghcr.io/pinhead001/notetime:latest --format='{{json .Config.Labels}}' | jq

# Run and check /version endpoint
docker run -d -p 8000:8000 ghcr.io/pinhead001/notetime:latest
curl http://localhost:8000/version
```

---

## Checking Render Deployment

To check what's deployed on Render:

**Option 1: Visit the version endpoint**
```
https://notetime.onrender.com/version
```

**Option 2: Check Render dashboard**
1. Go to https://dashboard.render.com
2. Select your notetime service
3. Click "Events" tab
4. See which commit was deployed

**Option 3: Check Render logs**
```bash
# If you have Render CLI installed
render logs -s notetime
```

---

## Image Tags from GitHub Actions

GitHub Actions creates these tags automatically:

| Push Type | Tags Created | Branch Info |
|-----------|-------------|-------------|
| Push to main | `latest`, `main-<sha>` | branch: main, commit: full SHA |
| Tag v1.0.0 | `1.0.0`, `1.0`, `1`, `latest` | branch: main, commit: full SHA |
| Pull Request | (no push) | branch: pr-123 |

**Example:**
```bash
# Pull specific commit build
docker pull ghcr.io/pinhead001/notetime:main-2e39a8c

# Check its info
curl http://localhost:8000/version
```

---

## Troubleshooting

### Version shows "unknown"

**Cause:** Image was built without build args

**Fix:** Rebuild with build args:
```bash
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
export GIT_COMMIT=$(git rev-parse --short HEAD)
docker-compose up --build
```

### Can't access /version endpoint

**Cause:** Old code version doesn't have the endpoint

**Fix:** Pull latest code and rebuild:
```bash
git pull origin claude/day-16-github-actions-KjgCH
docker-compose up --build
```

### Different info in labels vs API

**Cause:** Build args weren't passed to environment variables

**Fix:** Check Dockerfile has both LABEL and ENV lines for git info

---

## Quick Reference

```bash
# Check version API
curl http://localhost:8000/version

# Check image labels
docker inspect notetime-app --format='{{.Config.Labels}}'

# Check environment variables
docker exec notetime-app env | grep GIT

# Build with git info
export GIT_BRANCH=$(git branch --show-current)
export GIT_COMMIT=$(git rev-parse --short HEAD)
docker-compose up --build

# Check what branch you're on
git branch --show-current
git rev-parse --short HEAD
```

---

## Example Workflow

**Before deploying, check what you're building:**

```bash
# 1. Check current branch
git branch --show-current

# 2. Check last commit
git log -1 --oneline

# 3. Build with info
export GIT_BRANCH=$(git branch --show-current)
export GIT_COMMIT=$(git rev-parse --short HEAD)
docker-compose up --build

# 4. Verify build info
curl http://localhost:8000/version

# 5. If correct, merge to main
git checkout main
git merge your-branch
git push origin main
```

---

## Related Documentation

- [GitHub Actions](GITHUB-ACTIONS.md) - CI/CD pipeline
- [Docker Setup](DOCKER.md) - Docker configuration
- [Git Instructions](GIT-instructions.md) - Branch management
