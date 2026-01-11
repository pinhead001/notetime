from datetime import date, timedelta
from collections import defaultdict
from models import TaskSummary


def week_bounds(any_day: date) -> tuple[date, date]:
    """
    Returns (monday, sunday) for the week containing any_day.
    """
    monday = any_day - timedelta(days=any_day.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday
    
def summarize_week(tasks, work_entries, week_date: date) -> list[TaskSummary]:
    week_start, week_end = week_bounds(week_date)

    minutes_by_task: dict[str, int] = defaultdict(int)

    for entry in work_entries:
        if week_start <= entry.date <= week_end:
            minutes_by_task[entry.task_id] += entry.minutes

    summaries = []

    for task in tasks:
        total = minutes_by_task.get(task.id, 0)
        if total > 0:
            summaries.append(
                TaskSummary(
                    task_id=task.id,
                    task_name=task.name,
                    total_minutes=total
                )
            )

    return sorted(summaries, key=lambda s: s.total_minutes, reverse=True)