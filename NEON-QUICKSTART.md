# Neon Quick Start Guide

**Get up and running with Neon in 5 minutes.**

## Prerequisites
- Neon account (sign up at https://neon.tech)
- Python 3.8+ installed

## Quick Setup

### 1. Get Connection String
```bash
# From Neon console (https://console.neon.tech):
# 1. Select your project
# 2. Click "Connection Details"
# 3. Copy the connection string
```

### 2. Run Setup Script
```bash
# Interactive setup - will prompt for connection string
python scripts/setup_neon.py
```

**Or manually create .env:**
```bash
cp .env.example .env
# Edit .env and set your DATABASE_URL
```

### 3. Install & Initialize
```bash
# Install dependencies
pip install -r requirements.txt

# Create database tables
python -m notetime.create_db

# (Optional) Add demo data
python -m notetime.seed
```

### 4. Start Application
```bash
uvicorn notetime.main:app --reload
```

Visit http://localhost:8000/docs to test!

## Connection String Format

```
postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require
```

**Important:** Always include `?sslmode=require` for Neon connections.

## Deployment Options

### Vercel (Serverless)
Use Neon's **pooled connection string**:
```bash
vercel env add DATABASE_URL production
# Paste pooled connection string from Neon console
vercel --prod
```

### Docker
```bash
export DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require"
docker build -t notetime .
docker run -e DATABASE_URL=$DATABASE_URL -p 8000:8000 notetime
```

### Render / Traditional Hosting
Set `DATABASE_URL` environment variable in your hosting platform dashboard.

## Key Features

✅ **Automatic Connection Pooling** - Optimized for serverless
✅ **Scale to Zero** - Save costs when inactive
✅ **Instant Resume** - Database wakes automatically on first query
✅ **Database Branching** - Create branches like Git for testing
✅ **Auto Backups** - Built-in point-in-time recovery

## Configuration

The app is pre-configured for Neon with optimal settings:
- `pool_size: 2` - Small pool for serverless
- `pool_recycle: 60` - Short recycle for scale-to-zero
- `pool_pre_ping: True` - Verify connections before use
- `pool_timeout: 30` - Connection acquisition timeout

No changes needed! Settings are in `notetime/db.py`.

## Troubleshooting

### "Connection timeout"
✅ Check `?sslmode=require` is in connection string
✅ Try pooled connection string for serverless deployments

### "Too many connections"
✅ Use pooled connection string
✅ Reduce `pool_size` in `db.py`

### "SSL required"
✅ Add `?sslmode=require` to connection string

## Full Documentation

For detailed information, see [NEON-DEPLOYMENT.md](NEON-DEPLOYMENT.md)

## Support

- Neon Docs: https://neon.tech/docs
- Neon Discord: https://discord.gg/92vNTzKDGp
- SQLAlchemy + Neon: https://neon.tech/docs/guides/sqlalchemy
