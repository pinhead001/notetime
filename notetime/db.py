import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, MappedAsDataclass

# Database configuration
# Use PostgreSQL connection string from environment, fallback to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///notetime.db")

# Render and some providers use 'postgres://' but SQLAlchemy 1.4+ requires 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure engine based on database type
is_sqlite = "sqlite" in DATABASE_URL

# Engine configuration
engine_config = {
    "echo": False,
}

# SQLite-specific configuration
if is_sqlite:
    engine_config["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL-specific configuration
    engine_config.update({
        "pool_pre_ping": True,  # Verify connections before using them
        "pool_recycle": 300,    # Recycle connections after 5 minutes
        "pool_size": 5,         # Connection pool size
        "max_overflow": 10,     # Maximum overflow connections
    })

# Create engine
engine = create_engine(DATABASE_URL, **engine_config)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
class Base(MappedAsDataclass, DeclarativeBase):
    pass


# Database dependency for FastAPI
def get_db():
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
