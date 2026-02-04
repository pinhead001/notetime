# Running Notetime Docker Container on Windows (CMD)

This guide provides step-by-step instructions for running Notetime in Docker on Windows using Command Prompt (CMD).

## Prerequisites

### Step 1: Install Docker Desktop for Windows

1. **Download Docker Desktop**
   - Go to: https://www.docker.com/products/docker-desktop/
   - Click "Download for Windows"
   - Wait for `Docker Desktop Installer.exe` to download

2. **Install Docker Desktop**
   - Double-click `Docker Desktop Installer.exe`
   - Follow the installation wizard
   - Enable WSL 2 when prompted (recommended)
   - Click "Install"
   - Wait for installation to complete (5-10 minutes)

3. **Restart your computer** when prompted

4. **Start Docker Desktop**
   - Search for "Docker Desktop" in Windows Start menu
   - Click to open Docker Desktop
   - Wait for Docker engine to start (whale icon in system tray should be steady)
   - Accept the Docker Subscription Service Agreement

### Step 2: Verify Docker Installation

Open Command Prompt (CMD):
- Press `Win + R`
- Type `cmd`
- Press Enter

Run these commands to verify installation:

```cmd
docker --version
```
Expected output: `Docker version 24.x.x, build xxxxxxx`

```cmd
docker-compose --version
```
Expected output: `Docker Compose version v2.x.x` or `docker-compose version 1.x.x`

If you see version numbers, Docker is installed correctly! ✓

### Step 3: Get the Notetime Code

You should already have the code, but if not:

```cmd
cd C:\Users\YourUsername\Documents
git clone https://github.com/pinhead001/notetime.git
cd notetime
```

Or navigate to your existing notetime directory:

```cmd
cd C:\path\to\notetime
```

Example:
```cmd
cd C:\Users\John\Documents\notetime
```

## Running Notetime with Docker

### Method 1: Quick Start (Recommended)

**Step 1:** Open Command Prompt in the notetime directory

```cmd
cd C:\path\to\notetime
```

**Step 2:** Build and start the containers

```cmd
docker-compose up --build
```

**What this does:**
- Builds the Docker image (first time: 2-5 minutes)
- Creates PostgreSQL database container
- Creates Notetime application container
- Starts both containers
- Shows live logs in the terminal

**Step 3:** Wait for startup

You'll see output like:
```
Creating notetime-db ... done
Creating notetime-app ... done
Attaching to notetime-db, notetime-app
notetime-app | INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Step 4:** Open your browser

Go to: **http://localhost:8000**

You should see the Notetime application! 🎉

**Step 5:** Stop the containers

Press `Ctrl + C` in the Command Prompt window

To fully stop and remove containers:
```cmd
docker-compose down
```

### Method 2: Run in Background (Detached Mode)

If you want to run containers in the background and keep using Command Prompt:

**Step 1:** Start containers in detached mode

```cmd
docker-compose up -d --build
```

**Step 2:** Check containers are running

```cmd
docker-compose ps
```

You should see:
```
       Name                     Command              State           Ports
---------------------------------------------------------------------------------
notetime-app       uvicorn notetime.main:app ...   Up      0.0.0.0:8000->8000/tcp
notetime-db        docker-entrypoint.sh postgres   Up      5432/tcp
```

**Step 3:** View logs (optional)

```cmd
docker-compose logs -f
```

Press `Ctrl + C` to stop viewing logs (containers keep running)

**Step 4:** Stop containers when done

```cmd
docker-compose down
```

## Testing the Application

### Test in Browser

1. Open browser: http://localhost:8000
2. You should see the Notetime weekly view
3. Try adding a task or time entry

### Test from Command Prompt

**Test API is responding:**
```cmd
curl http://localhost:8000/
```

If you don't have `curl`, use PowerShell instead:
```powershell
Invoke-WebRequest http://localhost:8000/
```

Or just use your browser to visit http://localhost:8000/docs for API documentation.

## Common Commands

### Start Services
```cmd
docker-compose up -d
```

### Stop Services
```cmd
docker-compose down
```

### View Logs
```cmd
docker-compose logs
```

### View Live Logs
```cmd
docker-compose logs -f
```

### Restart Services
```cmd
docker-compose restart
```

### Rebuild After Code Changes
```cmd
docker-compose up -d --build
```

### Check Status
```cmd
docker-compose ps
```

### Access Database
```cmd
docker-compose exec db psql -U notetime -d notetime
```

Type `\q` to exit the database shell.

## Troubleshooting

### Issue 1: "docker: command not found"

**Problem:** Docker is not installed or not in PATH

**Solution:**
1. Install Docker Desktop (see Prerequisites)
2. Make sure Docker Desktop is running (check system tray)
3. Restart Command Prompt after installation
4. Try again

### Issue 2: Port 8000 is already in use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution 1 - Stop the other service:**
```cmd
netstat -ano | findstr :8000
```
Note the PID (last column), then:
```cmd
taskkill /PID <PID> /F
```

**Solution 2 - Use a different port:**

Edit `docker-compose.yml` and change:
```yaml
ports:
  - "8001:8000"  # Use port 8001 instead
```

Then access at: http://localhost:8001

### Issue 3: "docker-compose: command not found"

**Problem:** Using older Docker version

**Solution:** Use `docker compose` (with space) instead:
```cmd
docker compose up -d --build
docker compose down
docker compose logs
```

### Issue 4: Docker Desktop not starting

**Solution:**
1. Open Docker Desktop application
2. Wait for it to fully start (whale icon steady in system tray)
3. If stuck, restart Docker Desktop
4. If still stuck, restart Windows

### Issue 5: WSL 2 installation required

**Error:** "WSL 2 installation is incomplete"

**Solution:**
1. Open PowerShell as Administrator
2. Run: `wsl --install`
3. Restart computer
4. Start Docker Desktop again

### Issue 6: Cannot access http://localhost:8000

**Checklist:**
1. Are containers running?
   ```cmd
   docker-compose ps
   ```

2. Check container logs for errors:
   ```cmd
   docker-compose logs web
   ```

3. Try http://127.0.0.1:8000 instead

4. Make sure no firewall is blocking port 8000

5. Restart containers:
   ```cmd
   docker-compose restart
   ```

### Issue 7: "No space left on device"

**Solution:** Clean up Docker images and containers
```cmd
docker system prune -a
```

Type `y` to confirm. This removes all unused containers, images, and networks.

## Production Deployment on Windows

For production (running as a service):

**Step 1:** Create environment file

```cmd
copy .env.example .env
notepad .env
```

Edit the credentials:
```
POSTGRES_USER=notetime
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=notetime
APP_PORT=8000
ENVIRONMENT=production
```

Save and close.

**Step 2:** Start production services

```cmd
docker-compose -f docker-compose.prod.yml up -d --build
```

**Step 3:** Verify services are running

```cmd
docker-compose -f docker-compose.prod.yml ps
```

**Step 4:** View logs

```cmd
docker-compose -f docker-compose.prod.yml logs -f
```

## Database Management on Windows

### Backup Database

```cmd
docker-compose exec db pg_dump -U notetime notetime > backup.sql
```

The backup will be saved to: `C:\path\to\notetime\backup.sql`

### Restore Database

```cmd
type backup.sql | docker-compose exec -T db psql -U notetime notetime
```

### Reset Database (WARNING: Deletes all data!)

```cmd
docker-compose down
docker volume rm notetime_postgres_data
docker-compose up -d
```

## Performance Tips for Windows

1. **Use WSL 2 backend** (faster than Hyper-V)
   - Docker Desktop Settings → General → Use WSL 2 based engine

2. **Allocate more resources** if needed
   - Docker Desktop Settings → Resources
   - Increase Memory and CPU

3. **Enable file sharing** for volumes
   - Docker Desktop Settings → Resources → File Sharing
   - Add `C:\path\to\notetime`

4. **Disable antivirus scanning** for Docker directories (optional)
   - Exclude: `C:\Users\YourUsername\AppData\Local\Docker`

## Viewing Application in Windows

Once running, you can access:

- **Main Application:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Alternative API Docs:** http://localhost:8000/redoc

## Stopping and Cleaning Up

### Stop containers (keeps data)
```cmd
docker-compose down
```

### Stop containers and remove volumes (DELETES DATA!)
```cmd
docker-compose down -v
```

### Remove everything and start fresh
```cmd
docker-compose down -v
docker system prune -a
```

## Next Steps

Once you have the application running:

1. Create your first project
2. Add tasks for the week
3. Log time entries
4. Review weekly summary

For more details, see `DOCKER.md` for general Docker documentation.

## Getting Help

If you encounter issues:

1. Check Docker Desktop is running
2. View logs: `docker-compose logs`
3. Restart Docker Desktop
4. Restart your computer
5. Check the GitHub issues page

## Quick Reference Card

```cmd
# Start (first time)
docker-compose up --build

# Start (background)
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Check status
docker-compose ps

# Access application
# Browser: http://localhost:8000

# Rebuild after changes
docker-compose up -d --build
```

---

**Ready to go!** Open Command Prompt, navigate to the notetime directory, and run:

```cmd
docker-compose up --build
```

Then visit http://localhost:8000 in your browser! 🚀
