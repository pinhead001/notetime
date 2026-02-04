# Windows Quick Start Guide

**Get Notetime running on Windows in 5 minutes!**

## Prerequisites

1. **Install Docker Desktop**
   - Download: https://www.docker.com/products/docker-desktop/
   - Install and restart your computer
   - Start Docker Desktop (whale icon in system tray)

2. **Open Command Prompt**
   - Press `Win + R`
   - Type `cmd` and press Enter
   - Navigate to the notetime folder:
     ```cmd
     cd C:\path\to\notetime
     ```

## Option 1: Use the Helper Script (Easiest!)

Double-click `start-windows.bat` in Windows Explorer

OR from Command Prompt:
```cmd
start-windows.bat
```

Then choose option 1 or 2 to start the application.

## Option 2: Manual Commands

### Start Notetime (shows logs)
```cmd
docker-compose up --build
```

### Start Notetime (background)
```cmd
docker-compose up -d --build
```

### Stop Notetime
```cmd
docker-compose down
```

## Access the Application

Once started, open your browser to:

**http://localhost:8000**

## Need Help?

See detailed instructions in: `DOCKER-WINDOWS.md`

## Troubleshooting

**"docker: command not found"**
- Install Docker Desktop
- Make sure Docker Desktop is running

**"port is already allocated"**
- Another program is using port 8000
- Stop that program or edit docker-compose.yml to use a different port

**Can't access localhost:8000**
- Wait 30 seconds for containers to start
- Check containers are running: `docker-compose ps`
- View logs: `docker-compose logs`

## Quick Commands

```cmd
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Access database
docker-compose exec db psql -U notetime -d notetime
```

That's it! You're ready to use Notetime on Windows! 🎉
