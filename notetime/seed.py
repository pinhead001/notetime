from datetime import date, timedelta
from sqlalchemy import select
from notetime.db import SessionLocal
from notetime.models import Week, Project, Task

def seed():
    session = SessionLocal()

    # Determine current week (Monday)
    week_start = date.today() - timedelta(days=date.today().weekday())

    # Check if week already exists
    exists = session.scalar(
        select(Week).where(Week.start_date == week_start)
    )
    if exists:
        print("Week already exists.")
        return

    # Create seed data
    week = Week(start_date=week_start)
    project = Project(name="Notetime")

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
