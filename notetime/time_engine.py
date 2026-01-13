"""
Time Engine - Core time calculation functions.

Per MVP strategy: Python owns all time math, rounding, aggregation, rollover.
Frontend is dumb - just CRUD + display.

This is the heart of the application.
"""
from datetime import datetime, time, date
from math import ceil
from typing import List, Dict, Optional
from collections import defaultdict


def duration_minutes(start: time, end: time) -> int:
    """
    Calculate duration in minutes between two times.

    Args:
        start: Start time
        end: End time

    Returns:
        Duration in minutes (0 if end is before start)

    Example:
        >>> duration_minutes(time(9, 0), time(10, 30))
        90
    """
    start_mins = start.hour * 60 + start.minute
    end_mins = end.hour * 60 + end.minute
    return end_mins - start_mins if end_mins >= start_mins else 0


def round_quarter(minutes: int) -> int:
    """
    Round UP to nearest 15-minute increment.

    Per rules.md rounding policy:
    - 1-15 min → 15
    - 16-30 min → 30
    - 31-45 min → 45
    - 46-60 min → 60
    - etc.

    Args:
        minutes: Raw minutes worked

    Returns:
        Rounded minutes (0 if input <= 0)

    Example:
        >>> round_quarter(1)
        15
        >>> round_quarter(31)
        45
        >>> round_quarter(60)
        60
    """
    if minutes <= 0:
        return 0
    return ceil(minutes / 15) * 15


def minutes_to_hours(minutes: int) -> float:
    """
    Convert minutes to hours (decimal).

    Args:
        minutes: Total minutes

    Returns:
        Hours as decimal (e.g., 90 -> 1.5)

    Example:
        >>> minutes_to_hours(90)
        1.5
        >>> minutes_to_hours(45)
        0.75
    """
    return minutes / 60.0


def summarize_by_task_day(entries: List[Dict]) -> Dict[int, Dict]:
    """
    Group work entries by task and day.
    Apply rounding to daily totals only (per rules.md).

    Args:
        entries: List of work entry dicts with keys:
                 task_id, date, minutes

    Returns:
        {
            task_id: {
                "2024-01-08": 45,  # rounded
                "2024-01-09": 30,
                "total": 75
            }
        }

    Example:
        >>> entries = [
        ...     {"task_id": 1, "date": date(2024, 1, 8), "minutes": 32},
        ...     {"task_id": 1, "date": date(2024, 1, 8), "minutes": 10},
        ... ]
        >>> result = summarize_by_task_day(entries)
        >>> result[1]["2024-01-08"]
        45  # rounded from 42
    """
    # Group by task_id, then by date
    task_day_map = defaultdict(lambda: defaultdict(int))

    for entry in entries:
        task_id = entry["task_id"]
        entry_date = entry["date"]
        minutes = entry["minutes"]

        # Convert date to string for JSON serialization
        date_key = entry_date.isoformat() if isinstance(entry_date, date) else str(entry_date)

        # Accumulate minutes for this task+day
        task_day_map[task_id][date_key] += minutes

    # Apply rounding and calculate totals
    result = {}
    for task_id, day_minutes in task_day_map.items():
        result[task_id] = {}
        total = 0

        for day, minutes in day_minutes.items():
            rounded = round_quarter(minutes)
            result[task_id][day] = rounded
            total += rounded

        result[task_id]["total"] = total

    return result


def summarize_by_project(entries: List[Dict], tasks: List[Dict], projects: Dict[int, str]) -> Dict[str, Dict]:
    """
    Group work entries by project, then task.
    Convert to hours and organize by day of week.

    Args:
        entries: List of work entry dicts (task_id, date, minutes)
        tasks: List of task dicts (id, title, project_id)
        projects: Dict mapping project_id -> project_name

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

    Note:
        - Day abbreviations: Mon, Tue, Wed, Thu, Fri, Sat, Sun
        - Hours are decimal (e.g., 1.25 = 1h 15m)
        - Rounding applied before conversion
    """
    # Build task lookup: task_id -> (title, project_id)
    task_lookup = {
        task["id"]: (task["title"], task.get("project_id"))
        for task in tasks
    }

    # Group entries by project and task
    project_task_map = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for entry in entries:
        task_id = entry["task_id"]
        entry_date = entry["date"]
        minutes = entry["minutes"]

        # Get task info
        task_title, project_id = task_lookup.get(task_id, ("Unknown Task", None))
        project_name = projects.get(project_id, "No Project") if project_id else "No Project"

        # Get day of week abbreviation
        if isinstance(entry_date, date):
            day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][entry_date.weekday()]
        else:
            day_name = "Unknown"

        # Accumulate minutes
        project_task_map[project_name][task_title][day_name] += minutes

    # Apply rounding, convert to hours, calculate totals
    result = {}
    for project_name, tasks_data in project_task_map.items():
        result[project_name] = {}

        for task_title, day_minutes in tasks_data.items():
            result[project_name][task_title] = {}
            total_minutes = 0

            for day, minutes in day_minutes.items():
                rounded = round_quarter(minutes)
                hours = minutes_to_hours(rounded)
                result[project_name][task_title][day] = hours
                total_minutes += rounded

            result[project_name][task_title]["Total"] = minutes_to_hours(total_minutes)

    return result


def rollover_week(from_week_id: int, to_week_id: int, session) -> Dict[str, int]:
    """
    Rollover tasks from one week to the next based on state.

    Per rules.md:
    - COMPLETED → archive (stay in old week)
    - CANCELED → archive (stay in old week)
    - DELEGATED → stay in old week (no automatic carry)
    - ACTIVE → clone to next week

    Args:
        from_week_id: Source week ID
        to_week_id: Destination week ID
        session: SQLAlchemy session

    Returns:
        {"archived": 2, "carried": 3, "delegated": 1}

    Example:
        >>> from notetime.db import SessionLocal
        >>> session = SessionLocal()
        >>> counts = rollover_week(from_week_id=1, to_week_id=2, session=session)
        >>> print(f"Carried {counts['carried']} active tasks to next week")
    """
    from sqlalchemy import select
    from notetime.models import Task, TaskState

    # Query all tasks for the source week
    tasks_query = select(Task).where(Task.week_id == from_week_id)
    tasks = session.scalars(tasks_query).all()

    if not tasks:
        return {
            "archived": 0,
            "carried": 0,
            "delegated": 0
        }

    # Count tasks by state
    archived_count = 0
    carried_count = 0
    delegated_count = 0

    for task in tasks:
        if task.state == TaskState.ACTIVE.value:
            # Clone ACTIVE tasks to the new week
            new_task = Task(
                title=task.title,
                week_id=to_week_id,
                state=TaskState.ACTIVE.value,
                priority=task.priority,
                project_id=task.project_id,
                delegate=task.delegate
            )
            session.add(new_task)
            carried_count += 1

        elif task.state == TaskState.DELEGATED.value:
            # DELEGATED tasks stay in old week
            delegated_count += 1

        elif task.state in [TaskState.COMPLETED.value, TaskState.CANCELED.value]:
            # COMPLETED and CANCELED tasks are archived (stay in old week)
            archived_count += 1

    # Commit the new tasks
    session.commit()

    return {
        "archived": archived_count,
        "carried": carried_count,
        "delegated": delegated_count
    }
