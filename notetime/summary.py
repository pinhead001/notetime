"""
Weekly Summary Generator - Day 4 Deliverable

Generates project/task breakdown summaries for a given week.
Integrates with time_engine for all time calculations.
"""
from datetime import date
from typing import Dict, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from notetime.models import Week, Task, WorkEntry, Project
from notetime.time_engine import summarize_by_project


def generate_weekly_summary(week_id: int, session: Session) -> Dict:
    """
    Generate weekly summary for a given week.

    Queries all work entries for tasks in the specified week,
    then uses time_engine to calculate the project/task breakdown.

    Args:
        week_id: ID of the week to summarize
        session: SQLAlchemy session

    Returns:
        {
            "Project A": {
                "Task 1": {"Mon": 1.25, "Tue": 0.5, "Total": 1.75},
                "Task 2": {"Mon": 0.25, "Total": 0.25}
            },
            "No Project": {
                "Task 3": {"Wed": 2.0, "Total": 2.0}
            }
        }

    Example:
        >>> session = SessionLocal()
        >>> summary = generate_weekly_summary(week_id=1, session=session)
        >>> print(summary["Client Work"]["Development"]["Mon"])
        1.5
    """
    # Verify week exists
    week = session.get(Week, week_id)
    if not week:
        return {}

    # Get all tasks for this week
    tasks_query = select(Task).where(Task.week_id == week_id)
    tasks = session.scalars(tasks_query).all()

    if not tasks:
        return {}

    # Get all work entries for these tasks
    task_ids = [task.id for task in tasks]
    entries_query = select(WorkEntry).where(WorkEntry.task_id.in_(task_ids))
    work_entries = session.scalars(entries_query).all()

    if not work_entries:
        return {}

    # Format entries for time_engine
    entries_data = [
        {
            "task_id": entry.task_id,
            "date": entry.date,
            "minutes": entry.minutes
        }
        for entry in work_entries
    ]

    # Format tasks for time_engine
    tasks_data = [
        {
            "id": task.id,
            "title": task.title,
            "project_id": task.project_id
        }
        for task in tasks
    ]

    # Build project lookup: project_id -> project_name
    project_ids = [task.project_id for task in tasks if task.project_id is not None]
    projects_lookup = {}

    if project_ids:
        projects_query = select(Project).where(Project.id.in_(project_ids))
        projects = session.scalars(projects_query).all()
        projects_lookup = {project.id: project.name for project in projects}

    # Generate summary using time_engine
    summary = summarize_by_project(entries_data, tasks_data, projects_lookup)

    return summary


def get_weekly_totals(summary: Dict) -> Dict[str, float]:
    """
    Extract project totals from a weekly summary.

    Args:
        summary: Output from generate_weekly_summary()

    Returns:
        {"Project A": 5.25, "Project B": 3.0, "Total": 8.25}

    Example:
        >>> summary = generate_weekly_summary(1, session)
        >>> totals = get_weekly_totals(summary)
        >>> print(totals["Total"])
        8.25
    """
    project_totals = {}
    grand_total = 0.0

    for project_name, tasks in summary.items():
        project_total = 0.0
        for task_name, days in tasks.items():
            project_total += days.get("Total", 0.0)

        project_totals[project_name] = project_total
        grand_total += project_total

    project_totals["Total"] = grand_total
    return project_totals


def format_summary_text(summary: Dict) -> str:
    """
    Format summary as human-readable text.

    Args:
        summary: Output from generate_weekly_summary()

    Returns:
        Formatted text table

    Example:
        >>> text = format_summary_text(summary)
        >>> print(text)
        Project A
          Task 1: Mon 1.25h, Tue 0.50h | Total: 1.75h
          Task 2: Mon 0.25h | Total: 0.25h
        Project Total: 2.00h
    """
    if not summary:
        return "No time logged this week."

    lines = []

    for project_name, tasks in summary.items():
        lines.append(f"\n{project_name}")

        for task_name, days in tasks.items():
            day_parts = []
            total = days.get("Total", 0.0)

            # Get days in order (Mon-Sun)
            day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for day in day_order:
                if day in days:
                    hours = days[day]
                    day_parts.append(f"{day} {hours:.2f}h")

            day_str = ", ".join(day_parts) if day_parts else "No entries"
            lines.append(f"  {task_name}: {day_str} | Total: {total:.2f}h")

        # Project total
        project_total = sum(
            task_data.get("Total", 0.0)
            for task_data in tasks.values()
        )
        lines.append(f"Project Total: {project_total:.2f}h")

    # Grand total
    totals = get_weekly_totals(summary)
    lines.append(f"\n{'='*50}")
    lines.append(f"Week Total: {totals['Total']:.2f}h")

    return "\n".join(lines)
