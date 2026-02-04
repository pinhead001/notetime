# How to Pull Git Branch - Step by Step

## For Day 15 Docker Setup Branch

### Windows Command Prompt

**Step 1: Navigate to your notetime folder**
```cmd
cd C:\path\to\notetime
```

**Step 2: Fetch latest changes from remote**
```cmd
git fetch origin
```

**Step 3: Check out the Day 15 branch**
```cmd
git checkout claude/day-15-docker-setup-KjgCH
```

**Step 4: Pull the latest changes**
```cmd
git pull origin claude/day-15-docker-setup-KjgCH
```

**Done!** You now have the Docker setup files.

---

## Alternative: Start Fresh

If you want to start with a clean copy:

**Step 1: Save any local changes (if needed)**
```cmd
git stash
```

**Step 2: Fetch all branches**
```cmd
git fetch origin
```

**Step 3: Switch to the branch**
```cmd
git checkout claude/day-15-docker-setup-KjgCH
```

**Step 4: Reset to match remote exactly**
```cmd
git reset --hard origin/claude/day-15-docker-setup-KjgCH
```

---

## List Available Branches

**See all remote branches:**
```cmd
git branch -r
```

**See all local branches:**
```cmd
git branch
```

**See current branch:**
```cmd
git branch --show-current
```

---

## Switch Between Branches

**Switch to main:**
```cmd
git checkout main
git pull origin main
```

**Switch to Day 15 Docker branch:**
```cmd
git checkout claude/day-15-docker-setup-KjgCH
git pull origin claude/day-15-docker-setup-KjgCH
```

**Switch to Day 14 branch:**
```cmd
git checkout claude/day-14-usability-improvements-KjgCH
git pull origin claude/day-14-usability-improvements-KjgCH
```

---

## Verify You Have the Files

After pulling, check that Docker files exist:

```cmd
dir Dockerfile
dir docker-compose.yml
dir DOCKER-WINDOWS.md
dir start-windows.bat
```

You should see these files listed.

---

## Common Issues

### Issue: "Already on 'claude/day-15-docker-setup-KjgCH'"

You're already on the branch! Just pull latest changes:
```cmd
git pull
```

### Issue: "error: Your local changes would be overwritten"

Save your changes first:
```cmd
git stash
git pull
git stash pop
```

### Issue: "fatal: 'origin' does not appear to be a git repository"

Check your remote:
```cmd
git remote -v
```

If nothing shows, add the remote:
```cmd
git remote add origin https://github.com/pinhead001/notetime.git
```

### Issue: Branch doesn't exist locally

Fetch it from remote:
```cmd
git fetch origin
git checkout claude/day-15-docker-setup-KjgCH
```

---

## Quick Reference

```cmd
# Fetch all branches
git fetch origin

# List all branches
git branch -a

# Switch to branch
git checkout claude/day-15-docker-setup-KjgCH

# Pull latest changes
git pull

# Check current branch
git branch --show-current

# See what changed
git log --oneline -5
```

---

## After Pulling the Branch

Once you have the Day 15 branch, you can:

1. **Run Docker** (see WINDOWS-QUICKSTART.md)
   ```cmd
   docker-compose up --build
   ```

2. **Access application**
   http://localhost:8000

3. **Read documentation**
   - DOCKER-WINDOWS.md (detailed guide)
   - WINDOWS-QUICKSTART.md (quick start)
   - DOCKER.md (general Docker info)

---

## Complete Workflow Example

```cmd
REM 1. Navigate to project
cd C:\Users\John\Documents\notetime

REM 2. Fetch all branches
git fetch origin

REM 3. List available branches
git branch -r

REM 4. Switch to Day 15 branch
git checkout claude/day-15-docker-setup-KjgCH

REM 5. Pull latest changes
git pull

REM 6. Verify files exist
dir Docker*

REM 7. Start Docker
docker-compose up --build
```

---

## Need Help?

**Check git status:**
```cmd
git status
```

**See recent commits:**
```cmd
git log --oneline -5
```

**See what branch you're on:**
```cmd
git branch --show-current
```

**See all files in branch:**
```cmd
git ls-files
```
