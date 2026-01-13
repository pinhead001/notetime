#!/usr/bin/env python3
"""
Demo script for Day 4: Weekly Summary Generator

Creates sample data and demonstrates the weekly summary functionality.

Usage:
    python scripts/demo_summary.py
    OR
    python demo_summary.py (from scripts directory)
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import notetime module
# This allows running the script directly from scripts/ directory
script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from datetime import date, timedelta
from notetime.db import SessionLocal, engine
from notetime.models import Base, Week, Project, Task, WorkEntry
from notetime.summary import generate_weekly_summary, format_summary_text, get_weekly_totals


def create_sample_data():
    """Create sample week with tasks and work entries"""

    # Recreate database
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = SessionLocal()

    # Create week (current week)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week = Week(start_date=week_start)
    session.add(week)
    session.flush()

    print(f"Created week starting {week_start}")

    # Create projects
    client_project = Project(name="Client Work")
    internal_project = Project(name="Internal Projects")
    session.add(client_project)
    session.add(internal_project)
    session.flush()

    print(f"Created projects: {client_project.name}, {internal_project.name}")

    # Create tasks
    tasks_data = [
        ("Development", client_project.id, week.id),
        ("Code Review", client_project.id, week.id),
        ("Documentation", internal_project.id, week.id),
        ("Personal Research", None, week.id),  # No project
    ]

    tasks = []
    for title, project_id, week_id in tasks_data:
        task = Task(title=title, project_id=project_id, week_id=week_id)
        session.add(task)
        tasks.append(task)

    session.flush()
    print(f"Created {len(tasks)} tasks")

    # Create work entries across the week
    # Monday
    monday = week_start
    session.add(WorkEntry(task_id=tasks[0].id, date=monday, minutes=120))  # Development: 2h
    session.add(WorkEntry(task_id=tasks[0].id, date=monday, minutes=90))   # Development: 1.5h
    session.add(WorkEntry(task_id=tasks[1].id, date=monday, minutes=30))   # Code Review: 30m

    # Tuesday
    tuesday = week_start + timedelta(days=1)
    session.add(WorkEntry(task_id=tasks[0].id, date=tuesday, minutes=180))  # Development: 3h
    session.add(WorkEntry(task_id=tasks[2].id, date=tuesday, minutes=60))   # Documentation: 1h

    # Wednesday
    wednesday = week_start + timedelta(days=2)
    session.add(WorkEntry(task_id=tasks[1].id, date=wednesday, minutes=45))  # Code Review: 45m
    session.add(WorkEntry(task_id=tasks[2].id, date=wednesday, minutes=120)) # Documentation: 2h
    session.add(WorkEntry(task_id=tasks[3].id, date=wednesday, minutes=90))  # Personal: 1.5h

    # Thursday
    thursday = week_start + timedelta(days=3)
    session.add(WorkEntry(task_id=tasks[0].id, date=thursday, minutes=240))  # Development: 4h

    # Friday
    friday = week_start + timedelta(days=4)
    session.add(WorkEntry(task_id=tasks[1].id, date=friday, minutes=60))    # Code Review: 1h
    session.add(WorkEntry(task_id=tasks[2].id, date=friday, minutes=45))    # Documentation: 45m

    session.commit()
    print(f"Created work entries for Mon-Fri")

    week_id = week.id  # Get ID before closing session
    session.close()
    return week_id


def main():
    """Run the demo"""
    print("="*60)
    print("DAY 4: WEEKLY SUMMARY GENERATOR DEMO")
    print("="*60)

    # Create sample data
    print("\n1. Creating sample data...")
    week_id = create_sample_data()

    # Generate summary
    print(f"\n2. Generating summary for week {week_id}...")
    session = SessionLocal()
    summary = generate_weekly_summary(week_id, session)

    # Display JSON summary
    print("\n3. JSON Summary Output:")
    print("-" * 60)
    import json
    print(json.dumps(summary, indent=2))

    # Display formatted text
    print("\n4. Formatted Text Summary:")
    print("-" * 60)
    text = format_summary_text(summary)
    print(text)

    # Display project totals
    print("\n5. Project Totals:")
    print("-" * 60)
    totals = get_weekly_totals(summary)
    for project, hours in totals.items():
        print(f"{project}: {hours:.2f}h")

    session.close()

    print("\n" + "="*60)
    print("✓ Day 4 Demo Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
