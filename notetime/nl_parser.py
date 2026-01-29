"""
Natural Language Parser for Notebook-Style Entry
Parses entries like:
- "9-11 worked on API" → time entry from 9:00 to 11:00
- "2h fixed bug" → time entry for 2 hours
- "P1 deploy to production" → task with priority 1
- "@API update endpoints" → task with project
- "today 930-1200 client meeting" → time entry with date and times
"""
import re
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any


class EntryType:
    TASK = "task"
    TIME_LOG = "time_log"
    UNKNOWN = "unknown"


def parse_entry(text: str, current_week_id: int, default_task_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Parse natural language entry and return structured data.

    Returns:
        dict with keys:
        - type: "task" or "time_log"
        - data: dict with parsed fields
    """
    text = text.strip()
    if not text:
        return {"type": EntryType.UNKNOWN, "data": {}}

    # Try to parse as time entry first (most common notebook use case)
    time_entry = _parse_time_entry(text, current_week_id, default_task_id)
    if time_entry:
        return {"type": EntryType.TIME_LOG, "data": time_entry}

    # Parse as task
    task_entry = _parse_task_entry(text, current_week_id)
    if task_entry:
        return {"type": EntryType.TASK, "data": task_entry}

    return {"type": EntryType.UNKNOWN, "data": {}}


def _extract_project_task_from_description(description: str) -> tuple:
    """
    Extract @ProjectName and #TaskName from description.
    Returns: (project_name, task_name, cleaned_description)

    Example: "@API #UpdateEndpoints fixed bugs" → ("API", "UpdateEndpoints", "fixed bugs")
    """
    project_name = None
    task_name = None

    # Extract @ProjectName
    project_match = re.search(r'@(\w+)', description)
    if project_match:
        project_name = project_match.group(1)
        description = description.replace(project_match.group(0), '').strip()

    # Extract #TaskName
    task_match = re.search(r'#(\w+)', description)
    if task_match:
        task_name = task_match.group(1)
        description = description.replace(task_match.group(0), '').strip()

    return project_name, task_name, description


def _parse_time_entry(text: str, week_id: int, default_task_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Parse time entry formats:
    - "9-11 worked on API" → 9:00-11:00
    - "930-1200 client meeting" → 9:30-12:00
    - "2h fixed bug" → 2 hours duration
    - "today 9-11 worked on API"
    - "830-11 @ProjectName #TaskName description" → with project and task tagging
    """
    result = {}
    remaining_text = text

    # Extract date if present (today, yesterday, etc)
    entry_date = date.today()
    date_match = re.match(r'(today|yesterday)\s+(.+)', text, re.IGNORECASE)
    if date_match:
        date_str = date_match.group(1).lower()
        if date_str == "yesterday":
            entry_date = date.today() - timedelta(days=1)
        remaining_text = date_match.group(2)

    # Pattern 1: Time range (9-11, 930-1200, 9:30-11:00)
    time_range_pattern = r'^(\d{1,4}):?(\d{2})?\s*-\s*(\d{1,4}):?(\d{2})?\s+(.+)$'
    match = re.match(time_range_pattern, remaining_text)
    if match:
        start_hour, start_min, end_hour, end_min, description = match.groups()

        start_time = _parse_time_number(start_hour, start_min)
        end_time = _parse_time_number(end_hour, end_min)

        if start_time and end_time:
            # Calculate duration
            start_dt = datetime.combine(entry_date, start_time)
            end_dt = datetime.combine(entry_date, end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)  # Handle overnight shifts

            minutes = int((end_dt - start_dt).total_seconds() / 60)

            # Extract project and task from description
            project_name, task_name, cleaned_desc = _extract_project_task_from_description(description)

            return {
                "date": entry_date,
                "start_time": start_time,  # Return as time object, not string
                "end_time": end_time,      # Return as time object, not string
                "minutes": minutes,
                "note": cleaned_desc.strip(),
                "task_id": default_task_id,
                "project_name": project_name,
                "task_name": task_name
            }

    # Pattern 2: Duration (2h, 90m, 1.5h)
    duration_pattern = r'^(\d+\.?\d*)\s*(h|hr|hour|hours|m|min|mins|minutes)\s+(.+)$'
    match = re.match(duration_pattern, remaining_text, re.IGNORECASE)
    if match:
        amount, unit, description = match.groups()
        amount = float(amount)

        # Convert to minutes
        if unit.lower() in ['h', 'hr', 'hour', 'hours']:
            minutes = int(amount * 60)
        else:  # minutes
            minutes = int(amount)

        # Extract project and task from description
        project_name, task_name, cleaned_desc = _extract_project_task_from_description(description)

        return {
            "date": entry_date,
            "minutes": minutes,
            "note": cleaned_desc.strip(),
            "task_id": default_task_id,
            "project_name": project_name,
            "task_name": task_name
        }

    return None


def _parse_task_entry(text: str, week_id: int) -> Optional[Dict[str, Any]]:
    """
    Parse task entry formats:
    - "P1 deploy to production" → priority 1 task
    - "@API update endpoints" → task with project name
    - "deploy new feature" → regular task
    """
    result = {
        "week_id": week_id,
        "state": "active",
        "priority": 3,
        "project_id": None
    }

    remaining_text = text

    # Extract priority (P1, P2, etc)
    priority_match = re.match(r'[Pp]([1-5])\s+(.+)', remaining_text)
    if priority_match:
        result["priority"] = int(priority_match.group(1))
        remaining_text = priority_match.group(2)

    # Extract project (@ProjectName)
    project_match = re.match(r'@(\w+)\s+(.+)', remaining_text)
    if project_match:
        result["project_name"] = project_match.group(1)
        remaining_text = project_match.group(2)

    # Remaining text is the task title
    result["title"] = remaining_text.strip()

    # Only return if we have a title
    if result["title"]:
        return result

    return None


def _parse_time_number(hour_str: str, min_str: Optional[str] = None) -> Optional[time]:
    """
    Parse time from number strings.
    Examples:
    - "9", None → 09:00
    - "930", None → 09:30
    - "9", "30" → 09:30
    - "14", "45" → 14:45
    """
    try:
        if min_str:
            # Already split (e.g., "9", "30")
            hour = int(hour_str)
            minute = int(min_str)
        elif len(hour_str) <= 2:
            # Just hour (e.g., "9")
            hour = int(hour_str)
            minute = 0
        elif len(hour_str) == 3:
            # HMM format (e.g., "930")
            hour = int(hour_str[0])
            minute = int(hour_str[1:3])
        elif len(hour_str) == 4:
            # HHMM format (e.g., "1430")
            hour = int(hour_str[0:2])
            minute = int(hour_str[2:4])
        else:
            return None

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour=hour, minute=minute)
    except (ValueError, IndexError):
        pass

    return None
