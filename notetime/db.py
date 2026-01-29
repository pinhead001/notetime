from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, sessionmaker

from notetime.config import settings

# SQLite database path
# DATABASE_URL = "sqlite:///notetime.db"

# Handle SQLite-specific connect_args
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

# Engine
engine = create_engine(DATABASE_URL, echo=False)

# Session factory
SessionLocal = sessionmaker(bind=engine)


# Base class for ORM models
class Base(MappedAsDataclass, DeclarativeBase):
    pass
