from datetime import date
from data import tasks, work_entries
from summary import summarize_week

if __name__ == "__main__":
    summaries = summarize_week(tasks, work_entries, date(2026, 1, 6))

    for s in summaries:
        hours = s.total_minutes / 60
        print(f"{s.task_name}: {hours:.1f} hrs")