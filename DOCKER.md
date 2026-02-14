# Docker Deployment Guide for Notetime

This guide provides instructions for running Notetime locally using Docker and Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 or later)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0 or later)

To verify your installation:
```bash
docker --version
docker-compose --version
```

## Quick Start

### 1. Clone and Navigate to the Repository

```bash
cd /path/to/notetime
```

### 2. Configure Environment Variables (Optional)

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` to customize settings (optional for local development):
- `SECRET_KEY`: JWT secret key (auto-generated default is fine for local dev)
- `DATABASE_URL`: Already configured for Docker PostgreSQL
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time

### 3. Start the Application

Build and start all services:
```bash
docker-compose up --build
```

Or run in detached mode (background):
```bash
docker-compose up -d --build
```

### 4. Initialize the Database

On first run, initialize the database with sample data:
```bash
docker-compose exec web python -m notetime.seed
```

### 5. Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Docker Architecture

The setup includes two services:

### 1. **PostgreSQL Database** (`db` service)
- Image: `postgres:15-alpine`
- Port: `5432` (mapped to host)
- Database: `notetime`
- User: `notetime`
- Password: `notetime_dev_password`
- Data persistence: `postgres_data` volume

### 2. **FastAPI Web Application** (`web` service)
- Built from local `Dockerfile`
- Port: `8000` (mapped to host)
- Hot reload enabled for development
- Waits for database to be healthy before starting

## Common Commands

### Start Services
```bash
# Start in foreground (see logs)
docker-compose up

# Start in background
docker-compose up -d

# Rebuild and start
docker-compose up --build
```

### Stop Services
```bash
# Stop containers (preserves data)
docker-compose stop

# Stop and remove containers (preserves volumes)
docker-compose down

# Stop, remove containers AND volumes (deletes data)
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs

# Follow logs (live)
docker-compose logs -f

# Specific service
docker-compose logs web
docker-compose logs db
```

### Execute Commands in Containers
```bash
# Run Python commands
docker-compose exec web python -m notetime.seed

# Access Python shell
docker-compose exec web python

# Access PostgreSQL
docker-compose exec db psql -U notetime -d notetime

# Access container bash
docker-compose exec web bash
```

### Run Tests
```bash
# Run all tests
docker-compose exec web pytest

# Run with coverage
docker-compose exec web pytest --cov=notetime

# Run specific test file
docker-compose exec web pytest tests/test_time_engine.py
```

### Database Management

#### Backup Database
```bash
docker-compose exec db pg_dump -U notetime notetime > backup.sql
```

#### Restore Database
```bash
docker-compose exec -T db psql -U notetime notetime < backup.sql
```

#### Reset Database
```bash
# Stop services
docker-compose down

# Remove volume
docker volume rm notetime_postgres_data

# Start fresh
docker-compose up -d
docker-compose exec web python -m notetime.seed
```

#### Access Database Shell
```bash
docker-compose exec db psql -U notetime -d notetime
```

Common SQL commands:
```sql
-- List tables
\dt

-- Describe table
\d tasks

-- View data
SELECT * FROM tasks LIMIT 10;

-- Exit
\q
```

## Development Workflow

### Hot Reload

The application supports hot reload for development. When you modify Python files:
1. Docker Compose automatically detects changes
2. Uvicorn reloads the application
3. Changes are reflected immediately

No need to rebuild or restart containers.

### Debugging

#### View Application Logs
```bash
docker-compose logs -f web
```

#### View Database Logs
```bash
docker-compose logs -f db
```

#### Check Container Status
```bash
docker-compose ps
```

#### Inspect Container
```bash
docker-compose exec web env  # View environment variables
docker-compose exec web ls -la  # List files
```

## Troubleshooting

### Port Already in Use

**Error**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution**: Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Use port 8001 on host
```

Or stop the conflicting service:
```bash
# Find process using port 8000
lsof -i :8000
# or
sudo netstat -tlnp | grep :8000

# Kill the process
kill -9 <PID>
```

### Database Connection Issues

**Error**: `could not connect to server: Connection refused`

**Solutions**:
1. Wait for database to be healthy:
   ```bash
   docker-compose logs db
   ```
2. Restart services:
   ```bash
   docker-compose restart
   ```

### Permission Issues

**Error**: `Permission denied` when accessing files

**Solution**: Fix file permissions:
```bash
sudo chown -R $USER:$USER .
```

### Container Won't Start

**Check logs**:
```bash
docker-compose logs web
```

**Common fixes**:
```bash
# Rebuild without cache
docker-compose build --no-cache

# Remove all containers and volumes
docker-compose down -v
docker-compose up --build
```

### Out of Disk Space

**Check Docker disk usage**:
```bash
docker system df
```

**Clean up**:
```bash
# Remove unused containers, networks, images
docker system prune

# Remove unused volumes (WARNING: deletes data)
docker volume prune
```

## Production Considerations

**WARNING**: This Docker setup is optimized for local development, not production.

For production:
1. Use environment-specific `.env` files
2. Change default passwords
3. Use production-grade secret keys
4. Enable HTTPS/TLS
5. Configure proper logging
6. Set up monitoring and alerts
7. Use Docker secrets for sensitive data
8. Consider using managed database services
9. Implement proper backup strategies
10. Use Docker Swarm or Kubernetes for orchestration

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Set in docker-compose.yml | Yes |
| `SECRET_KEY` | JWT secret key | `dev-secret-key-change-in-production` | Yes |
| `ALGORITHM` | JWT algorithm | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | `10080` (7 days) | No |

## File Structure

```
notetime/
├── Dockerfile              # Application container definition
├── docker-compose.yml      # Multi-container orchestration
├── .dockerignore          # Files excluded from Docker build
├── .env.example           # Environment variables template
└── DOCKER.md              # This file
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [FastAPI in Containers](https://fastapi.tiangolo.com/deployment/docker/)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Docker logs: `docker-compose logs`
3. Open an issue on GitHub

---

**Last Updated**: 2026-02-10
