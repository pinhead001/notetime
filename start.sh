#!/bin/bash
# Notetime Docker Startup Script for Linux/Mac

set -e

echo "========================================"
echo "   Notetime Docker Startup (Unix)"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    echo ""
    echo "Please install Docker:"
    echo "  Linux: https://docs.docker.com/engine/install/"
    echo "  Mac: https://docs.docker.com/desktop/install/mac-install/"
    exit 1
fi

echo "[OK] Docker is installed"
echo ""

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo "ERROR: Docker is not running"
    echo ""
    echo "Please start Docker and try again."
    exit 1
fi

echo "[OK] Docker is running"
echo ""

# Capture git info for build metadata
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "local")
export GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "[INFO] Build info: $GIT_BRANCH @ $GIT_COMMIT"
echo ""

# Menu
echo "What would you like to do?"
echo ""
echo "1. Start Notetime (development mode, with logs)"
echo "2. Start Notetime (background mode)"
echo "3. Stop Notetime"
echo "4. Restart Notetime"
echo "5. View logs"
echo "6. Check status"
echo "7. Clean up (stop and remove containers)"
echo "8. Exit"
echo ""

read -p "Enter your choice (1-8): " choice

case $choice in
    1)
        echo ""
        echo "Starting Notetime in development mode..."
        echo "Press Ctrl+C to stop"
        echo ""
        docker-compose up --build
        ;;
    2)
        echo ""
        echo "Starting Notetime in background mode..."
        docker-compose up -d --build
        if [ $? -eq 0 ]; then
            echo ""
            echo "[SUCCESS] Notetime is starting!"
            echo ""
            echo "Wait a few seconds, then open your browser to:"
            echo "http://localhost:8000"
            echo ""
            echo "To view logs, run this script again and choose option 5"
            echo "To stop, run this script again and choose option 3"
        else
            echo ""
            echo "[ERROR] Failed to start Notetime"
            echo "Check the errors above"
        fi
        echo ""
        ;;
    3)
        echo ""
        echo "Stopping Notetime..."
        docker-compose down
        if [ $? -eq 0 ]; then
            echo ""
            echo "[SUCCESS] Notetime stopped"
        else
            echo ""
            echo "[ERROR] Failed to stop Notetime"
        fi
        echo ""
        ;;
    4)
        echo ""
        echo "Restarting Notetime..."
        docker-compose restart
        if [ $? -eq 0 ]; then
            echo ""
            echo "[SUCCESS] Notetime restarted"
            echo "Open your browser to: http://localhost:8000"
        else
            echo ""
            echo "[ERROR] Failed to restart Notetime"
        fi
        echo ""
        ;;
    5)
        echo ""
        echo "Showing Notetime logs (Press Ctrl+C to exit)..."
        echo ""
        docker-compose logs -f
        ;;
    6)
        echo ""
        echo "Checking Notetime status..."
        echo ""
        docker-compose ps
        echo ""
        ;;
    7)
        echo ""
        read -p "WARNING: This will stop and remove all containers. Continue? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            echo ""
            echo "Cleaning up..."
            docker-compose down
            echo ""
            echo "[SUCCESS] Cleanup complete"
        else
            echo ""
            echo "Cleanup cancelled"
        fi
        echo ""
        ;;
    8)
        echo ""
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "Done!"
