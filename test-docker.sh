#!/bin/bash
# Test script for Docker deployment

set -e

echo "=== Notetime Docker Build Test ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Docker is installed
echo "1. Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"
echo ""

# Test 2: Check Docker Compose is installed
echo "2. Checking Docker Compose installation..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is installed${NC}"
echo ""

# Test 3: Build Docker image
echo "3. Building Docker image..."
if docker build -t notetime:test . ; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
fi
echo ""

# Test 4: Check image size
echo "4. Checking image size..."
IMAGE_SIZE=$(docker images notetime:test --format "{{.Size}}")
echo "Image size: $IMAGE_SIZE"
echo ""

# Test 5: Start services with Docker Compose
echo "5. Starting services with Docker Compose..."
if docker-compose up -d --build; then
    echo -e "${GREEN}✓ Services started${NC}"
else
    echo -e "${RED}✗ Failed to start services${NC}"
    exit 1
fi
echo ""

# Wait for services to be healthy
echo "6. Waiting for services to be ready..."
sleep 10

# Test 6: Check database health
echo "7. Checking database health..."
DB_HEALTH=$(docker inspect notetime-db --format='{{.State.Health.Status}}')
if [ "$DB_HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✓ Database is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Database status: $DB_HEALTH${NC}"
fi
echo ""

# Test 7: Check web service is running
echo "8. Checking web service..."
if docker ps | grep -q notetime-app; then
    echo -e "${GREEN}✓ Web service is running${NC}"
else
    echo -e "${RED}✗ Web service is not running${NC}"
    docker-compose logs web
    exit 1
fi
echo ""

# Test 8: Test HTTP endpoint
echo "9. Testing HTTP endpoint..."
sleep 5  # Give app time to start
if curl -f -s http://localhost:8000/ > /dev/null; then
    echo -e "${GREEN}✓ Application is responding${NC}"
else
    echo -e "${RED}✗ Application is not responding${NC}"
    echo "Logs from web service:"
    docker-compose logs web
    docker-compose down
    exit 1
fi
echo ""

# Test 9: Test API docs endpoint
echo "10. Testing API docs endpoint..."
if curl -f -s http://localhost:8000/docs > /dev/null; then
    echo -e "${GREEN}✓ API docs are accessible${NC}"
else
    echo -e "${YELLOW}⚠ API docs endpoint failed${NC}"
fi
echo ""

# Test 10: Test database connection
echo "11. Testing database connection..."
if docker-compose exec -T db psql -U notetime -d notetime -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
fi
echo ""

# Test 11: Test API create operation
echo "12. Testing API create operation (create week)..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/weeks \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01"}')
if echo "$RESPONSE" | grep -q "id"; then
    echo -e "${GREEN}✓ API create operation successful${NC}"
else
    echo -e "${YELLOW}⚠ API create operation returned: $RESPONSE${NC}"
fi
echo ""

# Display logs
echo "13. Recent logs from web service:"
docker-compose logs --tail=20 web
echo ""

# Display container stats
echo "14. Container resource usage:"
docker stats --no-stream notetime-app notetime-db
echo ""

# Summary
echo "=== Test Summary ==="
echo -e "${GREEN}✓ Docker build test completed successfully!${NC}"
echo ""
echo "Services are running. You can:"
echo "  - Access the application: http://localhost:8000"
echo "  - Access API docs: http://localhost:8000/docs"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo ""

# Ask if user wants to keep services running
read -p "Keep services running? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping services..."
    docker-compose down
    echo -e "${GREEN}Services stopped${NC}"
else
    echo -e "${GREEN}Services are still running${NC}"
fi
