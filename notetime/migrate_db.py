"""
Database migration script - Add user authentication

This script drops and recreates the database with the new schema including user authentication.
WARNING: This will delete all existing data.

Usage:
    python -m notetime.migrate_db
"""
import os
from pathlib import Path
from notetime.db import Base, engine
from notetime.models import User, Week, Project, Task, WorkEntry


def migrate_database():
    """Drop and recreate database with new schema"""
    print("=" * 60)
    print("DATABASE MIGRATION: Adding User Authentication")
    print("=" * 60)
    print()
    print("WARNING: This will delete all existing data!")
    print()

    # Get database file path
    db_path = Path("notetime.db")

    # Check if database exists
    if db_path.exists():
        print(f"Found existing database: {db_path}")
        response = input("Delete and recreate? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            return

        # Delete the database file
        print(f"Deleting {db_path}...")
        os.remove(db_path)
        print("✓ Database deleted")
    else:
        print("No existing database found. Creating new database...")

    # Create all tables with new schema
    print("Creating tables with new schema...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")

    print()
    print("=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print()
    print("New schema includes:")
    print("  - users table")
    print("  - user_id foreign keys in weeks and projects")
    print("  - All data scoped per user")
    print()
    print("Next steps:")
    print("  1. Start the application: uvicorn notetime.main:app --reload")
    print("  2. Navigate to: http://localhost:8000/auth/register")
    print("  3. Create a new user account")
    print()


if __name__ == "__main__":
    migrate_database()
