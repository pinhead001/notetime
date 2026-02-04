# Docker Setup for Notetime

This guide explains how to build and run Notetime using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

## Quick Start

### 1. Build and Run with Docker Compose

```bash
# Build and start all services (PostgreSQL + Notetime)
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

The application will be available at: **http://localhost:8000**

### 2. Stop Services

```bash
# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (WARNING: deletes all data)
docker-compose down -v
```

## Configuration

### Environment Variables

The application uses the following environment variables (configured in `docker-compose.yml`):

- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://notetime:notetime@db:5432/notetime`)
- `ENVIRONMENT`: Application environment (default: `production`)

### Database

- **Database**: PostgreSQL 15
- **Default Credentials**:
  - User: `notetime`
  - Password: `notetime`
  - Database: `notetime`
  - Port: `5432`

**⚠️ For production, change these credentials!**

### Ports

- Web Application: `8000`
- PostgreSQL Database: `5432`

## Development Mode

The `docker-compose.yml` is configured for development with:
- Hot reload enabled (`--reload`)
- Code volumes mounted for live updates
- Database persisted in Docker volume

To make code changes:
1. Edit files locally
2. Uvicorn will automatically reload
3. Refresh browser to see changes

## Production Mode

For production deployment:

1. **Remove development volumes** from `docker-compose.yml`:
   ```yaml
   # Comment out or remove these lines:
   # volumes:
   #   - ./notetime:/app/notetime
   #   - ./templates:/app/templates
   #   - ./static:/app/static
   ```

2. **Remove --reload flag**:
   ```yaml
   command: uvicorn notetime.main:app --host 0.0.0.0 --port 8000
   ```

3. **Change database credentials** in `docker-compose.yml`

4. **Build and run**:
   ```bash
   docker-compose up -d --build
   ```

## Manual Docker Build

If you want to build and run without Docker Compose:

### Build Image

```bash
docker build -t notetime:latest .
```

### Run with SQLite (Standalone)

```bash
docker run -d \
  --name notetime-app \
  -p 8000:8000 \
  -v notetime-data:/app/data \
  notetime:latest
```

### Run with External PostgreSQL

```bash
docker run -d \
  --name notetime-app \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:password@host:5432/dbname" \
  -e ENVIRONMENT="production" \
  notetime:latest
```

## Database Management

### Access PostgreSQL Container

```bash
docker-compose exec db psql -U notetime -d notetime
```

### Backup Database

```bash
docker-compose exec db pg_dump -U notetime notetime > backup.sql
```

### Restore Database

```bash
docker-compose exec -T db psql -U notetime notetime < backup.sql
```

### Reset Database

```bash
# Stop services
docker-compose down

# Remove database volume
docker volume rm notetime_postgres_data

# Restart services (will create fresh database)
docker-compose up -d
```

## Troubleshooting

### Database Connection Issues

If you see database connection errors:

1. **Check database is healthy**:
   ```bash
   docker-compose ps
   ```
   Look for `healthy` status on the `db` service.

2. **View logs**:
   ```bash
   docker-compose logs db
   docker-compose logs web
   ```

3. **Verify database URL**:
   The app expects `DATABASE_URL` environment variable with correct PostgreSQL connection string.

### Port Already in Use

If port 8000 or 5432 is already in use:

1. **Change ports in `docker-compose.yml`**:
   ```yaml
   ports:
     - "8001:8000"  # Map to different host port
   ```

2. **Or stop conflicting services**:
   ```bash
   # Find process using port 8000
   lsof -i :8000

   # Kill the process
   kill -9 <PID>
   ```

### Container Won't Start

1. **Check logs**:
   ```bash
   docker-compose logs web
   ```

2. **Rebuild from scratch**:
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up
   ```

### File Permission Issues

If you encounter permission errors with mounted volumes:

```bash
# Fix permissions
sudo chown -R $USER:$USER .
```

## Testing the Build

### 1. Basic Smoke Test

```bash
# Start services
docker-compose up -d

# Wait for healthy status
sleep 10

# Test application is responding
curl http://localhost:8000/

# Check API docs
curl http://localhost:8000/docs

# View logs
docker-compose logs web

# Stop services
docker-compose down
```

### 2. Integration Test

```bash
# Start services
docker-compose up -d

# Create a week
curl -X POST http://localhost:8000/api/weeks \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01"}'

# Create a project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "is_active": true}'

# Stop services
docker-compose down
```

### 3. Performance Test

```bash
# Check resource usage
docker stats notetime-app notetime-db
```

## Health Checks

The database includes a health check that verifies PostgreSQL is ready:
- **Test**: `pg_isready -U notetime`
- **Interval**: 10 seconds
- **Timeout**: 5 seconds
- **Retries**: 5

The web service waits for the database to be healthy before starting.

## Image Size Optimization

Current setup uses `python:3.12-slim` base image for smaller size.

To further optimize:
- Use multi-stage builds
- Use `python:3.12-alpine` (smaller but may have compatibility issues)
- Minimize installed packages

## Security Considerations

For production deployment:

1. **Change default passwords** in `docker-compose.yml`
2. **Use secrets management** (Docker secrets, Kubernetes secrets, etc.)
3. **Don't expose database port** (remove `5432:5432` mapping)
4. **Use environment files** (`.env`) for sensitive data
5. **Enable SSL/TLS** for database connections
6. **Run container as non-root user**
7. **Scan images for vulnerabilities**:
   ```bash
   docker scan notetime:latest
   ```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
