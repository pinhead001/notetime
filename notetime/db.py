import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, sessionmaker

from notetime.config import settings

# SQLite database path
# DATABASE_URL = "sqlite:///notetime.db"

# Handle SQLite-specific connect_args

# POSTGRESQL setup
# 1. Get the URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Add a fallback for local testing (optional but recommended)
if not DATABASE_URL:
    # This creates a local file named 'test.db' if no URL is found
    DATABASE_URL = "sqlite:///./test.db"

# 3. Fix the postgres:// protocol if needed (Render uses postgres://, SQLAlchemy needs postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 4. Create the engine
engine = create_engine(DATABASE_URL, echo=False)

# Session factory
SessionLocal = sessionmaker(bind=engine)


# Base class for ORM models
class Base(MappedAsDataclass, DeclarativeBase):
    pass
