# Neon PostgreSQL Deployment Guide

This guide walks you through deploying Notetime with Neon, a serverless PostgreSQL platform.

## Why Neon?

- **Serverless**: Scales to zero when inactive, you only pay for what you use
- **Instant provisioning**: Database ready in seconds
- **Branching**: Create database branches like git branches for testing
- **Autoscaling**: Automatically scales compute based on load
- **Modern developer experience**: Great CLI, API, and web console

## Prerequisites

- A Neon account (sign up at https://neon.tech)
- Python 3.8+ installed locally
- Git installed

## Step 1: Create a Neon Project

1. Go to https://console.neon.tech
2. Click **New Project**
3. Choose:
   - **Project name**: `notetime` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Postgres version**: 16 (or latest stable)
4. Click **Create Project**

## Step 2: Get Your Connection String

After creating the project:

1. In the Neon console, go to your project dashboard
2. Click **Connection Details**
3. Select **Connection string** tab
4. Copy the connection string - it looks like:
   ```
   postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require
   ```
5. Save this securely - you'll need it in the next step

**Note**: Neon provides different connection strings for:
- **Direct connection**: For applications (what we'll use)
- **Pooled connection**: For serverless functions (optional, if deploying to Vercel/Lambda)

## Step 3: Configure Local Environment

1. Create a `.env` file in your project root (if it doesn't exist):
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your Neon connection string:
   ```bash
   DATABASE_URL=postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require
   SECRET_KEY=your-secret-key-change-this-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=10080
   ```

3. Generate a secure secret key:
   ```bash
   openssl rand -hex 32
   ```
   Copy the output and replace `your-secret-key-change-this-in-production` in `.env`

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

The application already includes `psycopg2-binary`, which works perfectly with Neon.

## Step 5: Initialize the Database

Run the database creation script to set up all tables:

```bash
python -m notetime.create_db
```

This will create all the necessary tables (users, weeks, tasks, work_entries, projects, feedback) in your Neon database.

**Optional**: Seed with demo data for testing:
```bash
python -m notetime.seed
```

## Step 6: Test the Connection

Start the application locally:

```bash
uvicorn notetime.main:app --reload
```

Visit http://localhost:8000/docs to see the API documentation and verify the connection works.

## Step 7: Deploy to Production

### Option A: Deploy to Render

1. Update `render.yaml` DATABASE_URL to use your Neon connection string:
   ```yaml
   envVars:
     - key: DATABASE_URL
       sync: false  # Set manually in Render dashboard
   ```

2. In Render dashboard, set the `DATABASE_URL` environment variable to your Neon connection string

3. Deploy following the instructions in `DEPLOYMENT.md`

### Option B: Deploy to Vercel

If deploying to Vercel (serverless):

1. Use Neon's **pooled connection string** instead:
   - In Neon console, go to Connection Details
   - Select **Pooled connection** tab
   - Copy the pooled connection string

2. Set environment variables in Vercel:
   ```bash
   vercel env add DATABASE_URL production
   ```
   Paste your Neon pooled connection string when prompted

3. Deploy:
   ```bash
   vercel --prod
   ```

### Option C: Deploy to Docker/VM

1. Add environment variable to your deployment:
   ```bash
   export DATABASE_URL="postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require"
   ```

2. Build and run:
   ```bash
   docker build -t notetime .
   docker run -e DATABASE_URL=$DATABASE_URL -p 8000:8000 notetime
   ```

## Step 8: Verify Production Database

1. Check that tables were created:
   - Go to Neon console → your project → **Tables**
   - You should see: users, weeks, tasks, work_entries, projects, feedback

2. Test the API endpoints:
   ```bash
   curl https://your-app-url.com/health
   ```

## Connection Pooling Configuration

The application is already optimized for Neon with these settings (in `notetime/db.py`):

```python
engine_config.update({
    "pool_pre_ping": True,    # Verify connections before use
    "pool_recycle": 60,       # Recycle connections every 60s
    "pool_size": 2,           # Small pool for serverless
    "max_overflow": 8,        # Allow burst traffic
    "pool_timeout": 30,       # Timeout for connection acquisition
})
```

These are optimized for Neon's serverless architecture and scale-to-zero behavior.

## Best Practices

### 1. Use Connection Pooling for Serverless

If deploying to serverless platforms (Vercel, AWS Lambda), use Neon's **pooled connection string** to avoid connection exhaustion.

### 2. Enable Autosuspend

In Neon console, configure autosuspend to save costs:
- Go to Project Settings → Compute
- Set **Autosuspend delay**: 5 minutes (or your preference)
- Database will pause after inactivity and resume instantly on next query

### 3. Monitor Usage

- Check the Neon dashboard for connection metrics
- Review query performance in the Neon console
- Set up alerts for connection limit warnings

### 4. Database Branching for Development

Neon supports database branches - perfect for testing migrations:

```bash
# Using Neon CLI
neonctl branches create --name dev-branch

# Get connection string for branch
neonctl connection-string dev-branch
```

Use the branch connection string in your local `.env` for testing.

### 5. Backups

Neon automatically backs up your data. To create a manual branch (instant snapshot):

```bash
neonctl branches create --name backup-$(date +%Y%m%d)
```

## Troubleshooting

### Connection Timeout

If you see connection timeout errors:

1. Check that `?sslmode=require` is in your connection string
2. Verify your IP isn't blocked (Neon allows all IPs by default)
3. Try using the pooled connection string

### Too Many Connections

If you hit connection limits:

1. Use Neon's pooled connection string for serverless deployments
2. Reduce `pool_size` in `db.py`
3. Check for connection leaks (ensure all database sessions are closed)

### Slow First Query After Inactivity

This is normal - Neon resumes from sleep on first query. Subsequent queries will be fast.

To avoid this in production:
- Reduce autosuspend delay
- Use a health check endpoint to keep the database warm
- Disable autosuspend for production (in Neon console)

## Migration from SQLite or Other PostgreSQL

If migrating from SQLite:

1. Export your SQLite data:
   ```bash
   sqlite3 notetime.db .dump > dump.sql
   ```

2. Convert SQLite syntax to PostgreSQL (manual step - adjust data types, sequences, etc.)

3. Import to Neon:
   ```bash
   psql "postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require" < dump.sql
   ```

If migrating from another PostgreSQL database:

1. Use `pg_dump`:
   ```bash
   pg_dump "old_database_url" > dump.sql
   ```

2. Import to Neon:
   ```bash
   psql "neon_connection_string" < dump.sql
   ```

## Cost Estimation

Neon Free Tier includes:
- 512 MB storage
- 1 shared vCPU
- Unlimited projects
- Autosuspend after inactivity

For production, Pro plan starts at $19/month with:
- 10 GB storage included
- Dedicated compute
- Longer history retention
- Higher connection limits

## Additional Resources

- [Neon Documentation](https://neon.tech/docs)
- [Neon CLI](https://neon.tech/docs/reference/cli)
- [SQLAlchemy with Neon](https://neon.tech/docs/guides/sqlalchemy)
- [Neon Status Page](https://status.neon.tech)

## Support

For Neon-specific issues:
- [Neon Discord](https://discord.gg/92vNTzKDGp)
- [Neon GitHub Discussions](https://github.com/neondatabase/neon/discussions)

For Notetime application issues:
- Check `KNOWN-ISSUES.md`
- Review `TESTING.md` for debugging steps
