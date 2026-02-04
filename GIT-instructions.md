# Git Instructions - Step by Step

Complete guide for working with Git branches, pulling, merging, and pushing changes.

## Table of Contents
1. [Pulling a Branch](#pulling-a-branch)
2. [Merging Branch to Main](#merging-branch-to-main)
3. [Switching Between Branches](#switching-between-branches)
4. [Common Issues](#common-issues)

---

## Pulling a Branch

### For Day 15 Docker Setup Branch

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

## Switching Between Branches

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

## Merging Branch to Main

### Method 1: Merge Locally and Push (Recommended)

This merges your feature branch into main on your local machine, then pushes to remote.

**Step 1: Make sure your feature branch is up to date**
```cmd
git checkout claude/day-15-docker-setup-KjgCH
git pull origin claude/day-15-docker-setup-KjgCH
```

**Step 2: Switch to main branch**
```cmd
git checkout main
```

**Step 3: Pull latest changes from main**
```cmd
git pull origin main
```

**Step 4: Merge the feature branch into main**
```cmd
git merge claude/day-15-docker-setup-KjgCH
```

If merge is successful, you'll see:
```
Merge made by the 'ort' strategy.
 X files changed, Y insertions(+), Z deletions(-)
```

**Step 5: Push merged main to remote**
```cmd
git push origin main
```

**Done!** Your changes are now in main on GitHub.

---

### Method 2: Fast-Forward Merge

If main hasn't changed since you created your branch, you can do a fast-forward merge:

**Step 1: Switch to main**
```cmd
git checkout main
git pull origin main
```

**Step 2: Merge with fast-forward**
```cmd
git merge --ff-only claude/day-15-docker-setup-KjgCH
```

**Step 3: Push to remote**
```cmd
git push origin main
```

---

### Method 3: Squash Merge (Clean History)

This combines all commits from the branch into one commit on main:

**Step 1: Switch to main**
```cmd
git checkout main
git pull origin main
```

**Step 2: Squash merge the feature branch**
```cmd
git merge --squash claude/day-15-docker-setup-KjgCH
```

**Step 3: Commit the squashed changes**
```cmd
git commit -m "Day 15: Add Docker containerization support"
```

**Step 4: Push to remote**
```cmd
git push origin main
```

---

### Complete Merge Workflow Example

```cmd
REM 1. Navigate to project
cd C:\Users\John\Documents\notetime

REM 2. Update feature branch
git checkout claude/day-15-docker-setup-KjgCH
git pull origin claude/day-15-docker-setup-KjgCH

REM 3. Switch to main
git checkout main
git pull origin main

REM 4. Merge feature branch
git merge claude/day-15-docker-setup-KjgCH

REM 5. Review the merge
git log --oneline -5

REM 6. Push to remote
git push origin main

REM 7. Verify it worked
git status
```

---

### After Merging to Main

**Option 1: Keep the feature branch**
```cmd
REM Just switch back to main
git checkout main
```

**Option 2: Delete the feature branch locally**
```cmd
REM Switch to main first
git checkout main

REM Delete local branch
git branch -d claude/day-15-docker-setup-KjgCH
```

**Option 3: Delete both local and remote branch**
```cmd
REM Switch to main
git checkout main

REM Delete local branch
git branch -d claude/day-15-docker-setup-KjgCH

REM Delete remote branch
git push origin --delete claude/day-15-docker-setup-KjgCH
```

---

### Resolving Merge Conflicts

If you encounter merge conflicts:

**Step 1: Git will show which files have conflicts**
```cmd
git status
```

**Step 2: Open conflicted files and look for markers**
```
<<<<<<< HEAD
(current main code)
=======
(your branch code)
>>>>>>> claude/day-15-docker-setup-KjgCH
```

**Step 3: Edit files to resolve conflicts**
- Remove the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
- Keep the code you want
- Save the file

**Step 4: Mark conflicts as resolved**
```cmd
git add filename.txt
```

**Step 5: Complete the merge**
```cmd
git commit
```

**Step 6: Push to remote**
```cmd
git push origin main
```

---

### Verify Merge Was Successful

**Check that main has your changes:**
```cmd
git checkout main
git log --oneline -10
```

You should see commits from your feature branch.

**Check files exist:**
```cmd
dir Dockerfile
dir docker-compose.yml
```

**Verify on GitHub:**
- Go to your repository on GitHub
- Click on the main branch
- Verify your files are there

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

### Branch Operations
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

### Merge Operations
```cmd
# Merge branch to main
git checkout main
git pull origin main
git merge claude/day-15-docker-setup-KjgCH
git push origin main

# Squash merge (single commit)
git checkout main
git merge --squash claude/day-15-docker-setup-KjgCH
git commit -m "Your message"
git push origin main

# Delete local branch
git branch -d branch-name

# Delete remote branch
git push origin --delete branch-name
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

## Complete Workflow Example - Pull and Test

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

**To merge to main:** See [Merging Branch to Main](#merging-branch-to-main) section above.

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
