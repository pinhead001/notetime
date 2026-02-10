from datetime import date, timedelta
from sqlalchemy import select
from notetime.db import SessionLocal, engine
from notetime.models import User, Week, Project, Task, Base

def seed():
    # Create all tables if they don't exist
    Base.metadata.create_all(engine)

    session = SessionLocal()

    # Create or get a test user
    user = session.scalar(select(User).where(User.email == "seed@example.com"))
    if not user:
        user = User(
            email="seed@example.com",
            username="seeduser",
            hashed_password="$2b$12$placeholder_hashed_password"
        )
        session.add(user)
        session.flush()
        print("Created seed user.")

    # Determine current week (Monday)
    week_start = date.today() - timedelta(days=date.today().weekday())

    # Check if week already exists for this user
    exists = session.scalar(
        select(Week).where(
            Week.start_date == week_start,
            Week.user_id == user.id
        )
    )
    if exists:
        print("Week already exists.")
        return

    # Create seed data
    week = Week(start_date=week_start, user_id=user.id)
    project = Project(name="Notetime", user_id=user.id)

    # Add week and project first to get IDs
    session.add(week)
    session.add(project)
    session.flush()  # Get auto-generated IDs

    # Now create task with week_id and project_id
    task = Task(title="Define core models", week_id=week.id, project_id=project.id)

    session.add(task)
    session.commit()
    session.close()

    print("Seed data created successfully.")

if __name__ == "__main__":
    seed()
