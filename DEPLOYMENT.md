# Notetime Deployment Guide for Vercel

This guide provides comprehensive instructions for deploying and managing the Notetime application on Vercel.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Database Considerations](#database-considerations)
- [Initial Setup](#initial-setup)
- [Environment Variables](#environment-variables)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Configuration](#post-deployment-configuration)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)

## Prerequisites

Before deploying to Vercel, ensure you have:

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI** (optional but recommended):
   ```bash
   npm install -g vercel
   ```
3. **GitHub Repository**: Your code should be in a GitHub repository
4. **Production Database**: Since SQLite doesn't work well with serverless, you'll need:
   - PostgreSQL (recommended: [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres))
   - Or another cloud database service

## Database Considerations

### Important: SQLite Limitation

**WARNING**: SQLite is NOT suitable for Vercel deployment due to its serverless architecture. Each function invocation creates a new instance, making persistent SQLite databases impractical.

### Recommended Database Solutions

#### Option 1: Vercel Postgres (Recommended)

Vercel Postgres is a managed PostgreSQL database that integrates seamlessly with Vercel deployments.

**Setup Steps:**

1. Navigate to your Vercel project dashboard
2. Go to **Storage** tab
3. Click **Create Database**
4. Select **Postgres**
5. Follow the setup wizard

**Benefits:**
- Automatic connection pooling
- Auto-scaling
- Built-in backups
- Zero-configuration integration

#### Option 2: External PostgreSQL Provider

Alternative PostgreSQL providers:
- [Supabase](https://supabase.com) (Free tier available)
- [Railway](https://railway.app) (Free tier available)
- [Neon](https://neon.tech) (Serverless Postgres)
- [AWS RDS](https://aws.amazon.com/rds/)
- [Google Cloud SQL](https://cloud.google.com/sql)

### Migrating from SQLite to PostgreSQL

1. **Update Dependencies**:

   Add to `requirements.txt`:
   ```
   psycopg2-binary==2.9.9
   ```

2. **Update Database Configuration**:

   Modify `notetime/db.py`:
   ```python
   import os
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker, DeclarativeBase

   # Use PostgreSQL connection string from environment
   DATABASE_URL = os.getenv(
       "DATABASE_URL",
       "sqlite:///./notetime.db"  # Fallback for local development
   )

   # Vercel Postgres URLs use 'postgres://' but SQLAlchemy requires 'postgresql://'
   if DATABASE_URL.startswith("postgres://"):
       DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

   engine = create_engine(
       DATABASE_URL,
       connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
       pool_pre_ping=True,
       pool_recycle=300,
   )

   SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

   class Base(DeclarativeBase):
       pass

   def get_db():
       db = SessionLocal()
       try:
           yield db
       finally:
           db.close()
   ```

3. **Run Migrations**:

   After deployment, initialize the database:
   ```bash
   vercel env pull .env.local
   python -c "from notetime.db import engine; from notetime.models import Base; Base.metadata.create_all(engine)"
   ```

## Initial Setup

### Step 1: Prepare Your Repository

Ensure your repository contains:
- `vercel.json` (already created)
- `api/index.py` (already created)
- `requirements.txt`
- `.vercelignore` (already created)
- `.env.example` (already created)

### Step 2: Link Repository to Vercel

**Via Vercel Dashboard:**

1. Log in to [vercel.com](https://vercel.com)
2. Click **"Add New Project"**
3. Import your GitHub repository
4. Select the repository containing Notetime
5. Configure project settings (see below)

**Via Vercel CLI:**

```bash
# Navigate to project directory
cd /path/to/notetime

# Login to Vercel
vercel login

# Deploy
vercel
```

## Environment Variables

### Required Environment Variables

Configure these in Vercel Dashboard → Settings → Environment Variables:

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | JWT secret key for authentication | Generate with `openssl rand -hex 32` | **Yes** |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` | **Yes** |
| `ALGORITHM` | JWT algorithm | `HS256` | No (defaults to HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time in minutes | `10080` (7 days) | No |

### Setting Environment Variables

**Via Vercel Dashboard:**

1. Go to Project → **Settings** → **Environment Variables**
2. Add each variable:
   - **Name**: Variable name (e.g., `SECRET_KEY`)
   - **Value**: Variable value
   - **Environment**: Select Production, Preview, and Development
3. Click **Save**

**Via Vercel CLI:**

```bash
# Set environment variable
vercel env add SECRET_KEY

# Pull environment variables locally
vercel env pull .env.local
```

### Generating SECRET_KEY

**On Linux/macOS:**
```bash
openssl rand -hex 32
```

**On Windows (PowerShell):**
```powershell
-join ((48..57) + (65..70) | Get-Random -Count 32 | % {[char]$_})
```

**In Python:**
```python
import secrets
print(secrets.token_hex(32))
```

## Deployment Steps

### Method 1: Automatic Deployment (Recommended)

1. **Connect GitHub Repository**: Link your repository in Vercel dashboard
2. **Configure Build Settings**:
   - **Framework Preset**: Other
   - **Build Command**: Leave empty
   - **Output Directory**: Leave empty
   - **Install Command**: `pip install -r requirements.txt`
3. **Set Environment Variables** (see above)
4. **Deploy**: Click **Deploy**

**Auto-Deploy**: Every push to `main` branch triggers automatic deployment.

### Method 2: Manual Deployment via CLI

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### Method 3: GitHub Actions Integration

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`).

**To enable automatic deployment:**

1. Uncomment the `deploy` job in `.github/workflows/ci.yml`
2. Add GitHub Secrets:
   - `VERCEL_TOKEN`: Your Vercel token (Settings → Tokens)
   - `VERCEL_ORG_ID`: Your organization ID
   - `VERCEL_PROJECT_ID`: Your project ID

Get org and project IDs:
```bash
vercel link
cat .vercel/project.json
```

## Post-Deployment Configuration

### 1. Initialize Database

After first deployment, initialize the database schema:

```bash
# Pull environment variables
vercel env pull .env.production

# Create tables
python -c "from notetime.db import engine; from notetime.models import Base; Base.metadata.create_all(engine)"
```

Or use the seed script:
```bash
python notetime/seed.py
```

### 2. Create First User

**Via API:**
```bash
curl -X POST https://your-app.vercel.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "SecurePassword123"
  }'
```

**Or visit**: `https://your-app.vercel.app/auth/register`

### 3. Verify Deployment

1. **Health Check**: Visit `https://your-app.vercel.app/docs` (API docs)
2. **Login**: Visit `https://your-app.vercel.app/auth/login`
3. **Create Test Data**: Create a week, project, and task

### 4. Configure Custom Domain (Optional)

1. Go to Project → **Settings** → **Domains**
2. Add your custom domain
3. Follow DNS configuration instructions
4. Update CORS settings if needed

## Monitoring and Maintenance

### Viewing Logs

**Via Vercel Dashboard:**
1. Go to Project → **Deployments**
2. Click on a deployment
3. View **Function Logs** or **Build Logs**

**Via Vercel CLI:**
```bash
vercel logs [deployment-url]
```

### Performance Monitoring

Monitor your deployment:
1. **Analytics**: Dashboard → Analytics
2. **Speed Insights**: Dashboard → Speed Insights
3. **Function Metrics**: Dashboard → Functions

### Database Maintenance

**Backup Database:**
- If using Vercel Postgres: Automatic backups included
- Manual backup:
  ```bash
  pg_dump $DATABASE_URL > backup.sql
  ```

**Restore Database:**
```bash
psql $DATABASE_URL < backup.sql
```

### Updating the Application

1. **Push changes to GitHub**: `git push origin main`
2. **Automatic deployment** triggers
3. **Monitor deployment** in Vercel dashboard
4. **Run migrations** if database schema changed

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Error**: `ModuleNotFoundError: No module named 'notetime'`

**Solution**: Ensure `api/index.py` correctly imports from notetime package.

#### 2. Database Connection Errors

**Error**: `could not connect to server`

**Solutions**:
- Verify `DATABASE_URL` environment variable
- Check database server is running
- Verify network connectivity
- Check connection pooling settings

#### 3. SQLite Errors in Production

**Error**: `sqlite3.OperationalError: unable to open database file`

**Solution**: Migrate to PostgreSQL (see Database Considerations section)

#### 4. Static Files Not Loading

**Error**: 404 on `/static/style.css`

**Solutions**:
- Verify `static/` directory is committed to git
- Check `vercel.json` static file routing
- Ensure `.vercelignore` doesn't exclude static files

#### 5. JWT Token Errors

**Error**: `Could not validate credentials`

**Solutions**:
- Verify `SECRET_KEY` is set correctly
- Check token expiration settings
- Clear cookies and re-login

#### 6. Cold Start Performance

**Issue**: First request is slow

**Explanation**: Serverless functions have cold starts (1-3 seconds)

**Solutions**:
- Use Vercel Pro for faster cold starts
- Implement database connection pooling
- Consider upgrading to Vercel Edge Functions

### Debug Mode

Enable debug logging:

```python
# In notetime/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Getting Help

1. **Vercel Support**: [vercel.com/support](https://vercel.com/support)
2. **GitHub Issues**: Open an issue in your repository
3. **Vercel Community**: [github.com/vercel/vercel/discussions](https://github.com/vercel/vercel/discussions)

## CI/CD Integration

The project includes a GitHub Actions workflow for continuous integration.

### Workflow Features

- **Automated Testing**: Runs all tests on push/PR
- **Code Quality**: Linting and formatting checks
- **Security Scanning**: Dependency and code security checks
- **Multi-Python Version Testing**: Tests on Python 3.11 and 3.12
- **Coverage Reporting**: Uploads coverage to Codecov

### Running CI Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov=notetime

# Run linter
ruff check notetime/ tests/

# Run formatter
ruff format notetime/ tests/ --check
```

## Production Best Practices

### Security

1. **Always use HTTPS**: Vercel provides this automatically
2. **Rotate SECRET_KEY**: Change periodically
3. **Use strong passwords**: Enforce password policies
4. **Enable rate limiting**: Prevent brute force attacks
5. **Monitor logs**: Watch for suspicious activity

### Performance

1. **Enable caching**: Use Vercel's Edge Network
2. **Optimize queries**: Add database indexes
3. **Connection pooling**: Use pgbouncer for PostgreSQL
4. **Minimize bundle size**: Keep dependencies lean

### Scalability

1. **Database scaling**: Use connection pooling
2. **Monitor function execution time**: Stay under limits
3. **Implement pagination**: For large datasets
4. **Use CDN**: Serve static assets from edge

### Reliability

1. **Set up monitoring**: Use Vercel Analytics
2. **Configure alerts**: For errors and downtime
3. **Regular backups**: Automate database backups
4. **Test disaster recovery**: Practice restoration

## Cost Optimization

### Vercel Free Tier Limits

- **100 GB bandwidth** per month
- **100 hours** of serverless function execution time
- **6,000 function invocations** per day
- **Unlimited** static requests

### Tips to Stay Within Free Tier

1. **Optimize function execution**: Reduce runtime
2. **Cache responses**: Use HTTP caching headers
3. **Minimize database queries**: Use efficient queries
4. **Compress responses**: Enable gzip compression

### Upgrading

When you need more:
- **Vercel Pro**: $20/month (per user)
- **Vercel Enterprise**: Custom pricing

## Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Vercel Postgres Guide](https://vercel.com/docs/storage/vercel-postgres)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Notetime GitHub Repository](https://github.com/yourusername/notetime)

---

**Last Updated**: 2026-02-08

For questions or issues, please open an issue on GitHub or contact the development team.
