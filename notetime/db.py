import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, MappedAsDataclass

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------
# The DATABASE_URL is a connection string that tells SQLAlchemy where the
# database lives and what driver to use:
#   - SQLite (local dev):   "sqlite:///notetime.db"       → creates a file on disk
#   - PostgreSQL (prod):    "postgresql://user:pass@host/dbname"
#
# os.getenv() reads the value from an environment variable, falling back to
# the SQLite path when no environment variable is set (i.e. local dev).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///notetime.db")

# Some hosting providers (Render) provide a legacy "postgres://" URL prefix,
# but SQLAlchemy 1.4+ requires "postgresql://". Fix it here so the app works
# regardless of which form the provider gives us.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Flag used below to apply database-specific settings.
is_sqlite = "sqlite" in DATABASE_URL

# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------
# The *engine* is the low-level object responsible for opening and closing
# actual TCP/file connections to the database. Think of it as the database
# connection factory.
#
# "echo=False" means SQLAlchemy won't print every SQL statement it runs.
# Set to True during debugging if you want to see the raw SQL.
engine_config = {
    "echo": False,
}

if is_sqlite:
    # SQLite only allows one thread to use a connection at a time by default.
    # FastAPI handles requests on multiple threads, so we disable that check.
    # This is safe here because SQLAlchemy's session management handles
    # concurrency correctly at a higher level.
    engine_config["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL-specific connection pool settings:
    #   pool_pre_ping  – Before handing a connection from the pool to your
    #                    code, send a lightweight "ping" to verify it's still
    #                    alive. Prevents errors after the DB restarts or drops
    #                    idle connections.
    #   pool_recycle   – Force connections to be closed and reopened after
    #                    this many seconds (300 = 5 min). Prevents stale
    #                    connections from accumulating.
    #   pool_size      – How many persistent connections to keep open in the
    #                    pool. Requests grab one from here instead of opening
    #                    a new TCP connection every time.
    #   max_overflow   – Extra connections allowed above pool_size when all
    #                    pool slots are busy. They're closed when released.
    engine_config.update({
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    })

# Create the engine using the URL and settings built above.
engine = create_engine(DATABASE_URL, **engine_config)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
# A *session* is the day-to-day workhorse: it tracks which ORM objects have
# been created/modified and translates those changes into SQL when you call
# session.commit().
#
# sessionmaker() produces a *class* (not an instance) that we call later to
# create individual sessions:
#   db = SessionLocal()   ← creates one session
#
#   autocommit=False  – Don't write changes to the DB automatically; we
#                       call db.commit() explicitly so we control when data
#                       is persisted.
#   autoflush=False   – Don't automatically send pending SQL to the DB before
#                       each query. We control flushing manually.
#   bind=engine       – All sessions created by this factory connect through
#                       the engine above.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# ORM base class
# ---------------------------------------------------------------------------
# All SQLAlchemy ORM model classes (User, Week, Task, …) inherit from Base.
# This inheritance:
#   1. Registers the model with SQLAlchemy's metadata so that
#      Base.metadata.create_all(engine) knows what tables to create.
#   2. MappedAsDataclass automatically generates __init__, __repr__, etc.
#      from the mapped columns — similar to Python dataclasses.
class Base(MappedAsDataclass, DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency: get_db
# ---------------------------------------------------------------------------
# FastAPI uses *dependency injection* to share resources across route
# handlers. Any route function that declares `db: Session = Depends(get_db)`
# will automatically receive a fresh database session for that request.
#
# How it works:
#   1. FastAPI calls get_db() before the route function runs.
#   2. get_db() opens a session and *yields* it to the route function.
#      "yield" pauses the generator here and hands the value to the caller.
#   3. The route function runs with access to `db`.
#   4. After the route returns (or raises an error), execution resumes in
#      get_db() after the yield, where the session is always closed via
#      the finally block — preventing connection leaks.
def get_db():
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
