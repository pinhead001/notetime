#!/usr/bin/env python3
"""
Demo script for Day 5: Rollover Engine

Demonstrates rolling over tasks from one week to the next based on their state.

Usage:
    python scripts/demo_rollover.py
    OR
    python demo_rollover.py (from scripts directory)
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import notetime module
script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from datetime import date, timedelta
from notetime.db import SessionLocal, engine
from notetime.models import Base, Week, Project, Task, TaskState
from notetime.time_engine import rollover_week


def create_demo_data():
    """Create sample data with two weeks and various task states"""

    # Recreate database
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = SessionLocal()

    # Create two consecutive weeks
    week1_start = date(2024, 1, 8)  # Monday
    week2_start = week1_start + timedelta(days=7)

    week1 = Week(start_date=week1_start)
    week2 = Week(start_date=week2_start)
    session.add_all([week1, week2])
    session.flush()

    print(f"Created Week 1: {week1_start}")
    print(f"Created Week 2: {week2_start}\n")

    # Create projects
    client_project = Project(name="Client Work")
    internal_project = Project(name="Internal")
    session.add_all([client_project, internal_project])
    session.flush()

    # Create tasks in various states
    tasks = [
        # Active tasks (should carry over)
        Task(
            title="Implement API endpoints",
            week_id=week1.id,
            state=TaskState.ACTIVE.value,
            priority=1,
            project_id=client_project.id
        ),
        Task(
            title="Write documentation",
            week_id=week1.id,
            state=TaskState.ACTIVE.value,
            priority=2,
            project_id=internal_project.id
        ),
        Task(
            title="Review pull requests",
            week_id=week1.id,
            state=TaskState.ACTIVE.value,
            priority=3
        ),

        # Completed tasks (should be archived)
        Task(
            title="Set up development environment",
            week_id=week1.id,
            state=TaskState.COMPLETED.value,
            project_id=client_project.id
        ),
        Task(
            title="Initial project planning",
            week_id=week1.id,
            state=TaskState.COMPLETED.value,
            project_id=internal_project.id
        ),

        # Canceled task (should be archived)
        Task(
            title="Old feature we decided not to build",
            week_id=week1.id,
            state=TaskState.CANCELED.value
        ),

        # Delegated task (should stay in old week)
        Task(
            title="Waiting for client feedback",
            week_id=week1.id,
            state=TaskState.DELEGATED.value,
            delegate="Client Team"
        ),
    ]

    session.add_all(tasks)
    session.commit()

    print("Created tasks in Week 1:")
    print(f"  - 3 ACTIVE tasks")
    print(f"  - 2 COMPLETED tasks")
    print(f"  - 1 CANCELED task")
    print(f"  - 1 DELEGATED task")
    print(f"  Total: 7 tasks\n")

    # Capture IDs before closing session
    week1_id = week1.id
    week2_id = week2.id
    session.close()
    return week1_id, week2_id


def display_week_tasks(week_id: int, week_name: str):
    """Display all tasks for a given week"""
    session = SessionLocal()

    from sqlalchemy import select
    tasks = session.scalars(
        select(Task).where(Task.week_id == week_id)
    ).all()

    print(f"\n{week_name} Tasks ({len(tasks)} total):")
    print("-" * 60)

    if not tasks:
        print("  (no tasks)")
    else:
        # Group by state
        by_state = {}
        for task in tasks:
            if task.state not in by_state:
                by_state[task.state] = []
            by_state[task.state].append(task)

        # Display grouped by state
        for state in [TaskState.ACTIVE.value, TaskState.COMPLETED.value,
                      TaskState.CANCELED.value, TaskState.DELEGATED.value]:
            if state in by_state:
                print(f"\n  {state.upper()}:")
                for task in by_state[state]:
                    project_info = ""
                    if task.project:
                        project_info = f" [{task.project.name}]"
                    delegate_info = ""
                    if task.delegate:
                        delegate_info = f" (delegated to: {task.delegate})"

                    print(f"    • {task.title}{project_info}{delegate_info}")

    session.close()


def main():
    """Run the demo"""
    print("=" * 60)
    print("DAY 5: ROLLOVER ENGINE DEMO")
    print("=" * 60)
    print()

    # Step 1: Create demo data
    print("1. Creating demo data...")
    week1_id, week2_id = create_demo_data()

    # Step 2: Display Week 1 before rollover
    print("\n" + "=" * 60)
    print("BEFORE ROLLOVER")
    print("=" * 60)
    display_week_tasks(week1_id, "Week 1")
    display_week_tasks(week2_id, "Week 2")

    # Step 3: Perform rollover
    print("\n\n" + "=" * 60)
    print("PERFORMING ROLLOVER")
    print("=" * 60)
    session = SessionLocal()
    counts = rollover_week(
        from_week_id=week1_id,
        to_week_id=week2_id,
        session=session
    )
    session.close()

    print(f"\nRollover Results:")
    print(f"  ✓ Carried forward: {counts['carried']} tasks (ACTIVE)")
    print(f"  📦 Archived: {counts['archived']} tasks (COMPLETED/CANCELED)")
    print(f"  ⏸  Delegated: {counts['delegated']} tasks (stayed in old week)")
    print(f"  Total processed: {sum(counts.values())} tasks")

    # Step 4: Display after rollover
    print("\n" + "=" * 60)
    print("AFTER ROLLOVER")
    print("=" * 60)
    display_week_tasks(week1_id, "Week 1")
    display_week_tasks(week2_id, "Week 2")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Per rules.md rollover policy:
  • ACTIVE tasks → Cloned to next week (continue working)
  • COMPLETED tasks → Archived in old week (finished)
  • CANCELED tasks → Archived in old week (no longer needed)
  • DELEGATED tasks → Stay in old week (waiting for someone else)

Week 1 retains all original tasks (historical record).
Week 2 receives only the ACTIVE tasks (fresh start).
""")

    print("=" * 60)
    print("✓ Day 5 Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
