# Automatic Build Info Tracking

Build information (git branch, commit, date) is now automatically captured when building Docker images!

## How It Works

All build scripts automatically capture git information and pass it to Docker:

### Windows (start-windows.bat)
```batch
start-windows.bat
```
Automatically captures `GIT_BRANCH` and `GIT_COMMIT` before running docker-compose.

### Linux/Mac (start.sh)
```bash
./start.sh
```
Automatically exports `GIT_BRANCH`, `GIT_COMMIT`, and `BUILD_DATE` environment variables.

### Makefile
```bash
make build
make dev
make prod
```
Automatically exports git info for all docker-compose commands.

---

## Quick Start

**Just run the startup script - no manual setup needed!**

### Windows
```powershell
# Double-click start-windows.bat
# OR from PowerShell:
.\start-windows.bat
```

### Linux/Mac
```bash
./start.sh
```

### Using Make
```bash
make dev      # Development mode with logs
make build    # Just build
make up       # Start in background
```

---

## Verification

Once running, check the build info:

**Method 1: API Endpoint**
```bash
curl http://localhost:8000/version
```

**Method 2: Docker Inspect**
```bash
docker inspect notetime-app --format='{{.Config.Labels}}'
```

**Method 3: Environment Variables**
```bash
docker exec notetime-app env | grep GIT
```

---

## What Gets Captured

| Variable | Value | Example |
|----------|-------|---------|
| `GIT_BRANCH` | Current git branch | `claude/day-16-github-actions-KjgCH` |
| `GIT_COMMIT` | Short commit SHA | `04dfe34` |
| `BUILD_DATE` | ISO 8601 timestamp | `2024-02-04T19:23:45Z` |

---

## Manual Override (Optional)

If you want to set specific values:

**Windows PowerShell:**
```powershell
$env:GIT_BRANCH = "my-branch"
$env:GIT_COMMIT = "abc1234"
docker-compose up --build
```

**Linux/Mac:**
```bash
export GIT_BRANCH="my-branch"
export GIT_COMMIT="abc1234"
docker-compose up --build
```

---

## Direct docker-compose (Without Scripts)

If you run `docker-compose` directly without the startup scripts or Makefile:

```bash
docker-compose up --build
```

Build info will use **fallback defaults**:
- `GIT_BRANCH`: "local"
- `GIT_COMMIT`: "dev"
- `BUILD_DATE`: "unknown"

**To get automatic capture:**
```bash
# Linux/Mac
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
export GIT_COMMIT=$(git rev-parse --short HEAD)
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
docker-compose up --build

# Windows PowerShell
$env:GIT_BRANCH = git rev-parse --abbrev-ref HEAD
$env:GIT_COMMIT = git rev-parse --short HEAD
docker-compose up --build
```

---

## GitHub Actions (Always Automatic)

When images are built by GitHub Actions, build info is **always** automatic:

```yaml
build-args: |
  GIT_BRANCH=${{ github.ref_name }}
  GIT_COMMIT=${{ github.sha }}
  BUILD_DATE=${{ steps.timestamp.outputs.build_date }}
```

No configuration needed!

---

## Troubleshooting

### "git not found" or build info shows "local/dev"

**Cause:** Git is not installed or not in PATH, OR you ran docker-compose directly

**Solution 1:** Use the startup scripts (they handle this automatically)
```bash
./start.sh              # Linux/Mac
start-windows.bat       # Windows
```

**Solution 2:** Install git
- Windows: https://git-scm.com/download/win
- Mac: `brew install git`
- Linux: `sudo apt install git`

**Solution 3:** Use Makefile
```bash
make dev
```

### Build info not updating after switching branches

**Cause:** Docker is using cached values

**Fix:** Rebuild without cache
```bash
docker-compose build --no-cache
```

Or use startup script option 7 (Clean up) then rebuild.

---

## Summary

✅ **Startup scripts automatically capture git info**
✅ **Makefile automatically exports git variables**
✅ **GitHub Actions automatically includes build metadata**
✅ **No manual configuration needed**
✅ **Check with `/version` endpoint**

**Recommended:** Use `start-windows.bat`, `start.sh`, or `make dev` for automatic build info!
