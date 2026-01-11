"""
Tests for time_engine module.

Run with: pytest tests/test_time_engine.py
Or: python -m pytest tests/
"""
import pytest
from datetime import time, date
from notetime.time_engine import (
    duration_minutes,
    round_quarter,
    minutes_to_hours,
    summarize_by_task_day,
    summarize_by_project
)


class TestDurationMinutes:
    """Test duration calculation between times"""

    def test_basic_duration(self):
        """Test simple duration calculation"""
        assert duration_minutes(time(9, 0), time(10, 30)) == 90
        assert duration_minutes(time(14, 15), time(14, 45)) == 30

    def test_full_hour(self):
        """Test full hour durations"""
        assert duration_minutes(time(9, 0), time(10, 0)) == 60
        assert duration_minutes(time(13, 0), time(17, 0)) == 240

    def test_same_time(self):
        """Test when start and end are the same"""
        assert duration_minutes(time(10, 0), time(10, 0)) == 0

    def test_end_before_start(self):
        """Test when end is before start (should return 0)"""
        assert duration_minutes(time(17, 0), time(9, 0)) == 0


class TestRoundQuarter:
    """Test 15-minute rounding (always round UP)"""

    def test_round_up_to_15(self):
        """1-15 minutes rounds to 15"""
        assert round_quarter(1) == 15
        assert round_quarter(7) == 15
        assert round_quarter(15) == 15

    def test_round_up_to_30(self):
        """16-30 minutes rounds to 30"""
        assert round_quarter(16) == 30
        assert round_quarter(23) == 30
        assert round_quarter(30) == 30

    def test_round_up_to_45(self):
        """31-45 minutes rounds to 45"""
        assert round_quarter(31) == 45
        assert round_quarter(38) == 45
        assert round_quarter(45) == 45

    def test_round_up_to_60(self):
        """46-60 minutes rounds to 60"""
        assert round_quarter(46) == 60
        assert round_quarter(53) == 60
        assert round_quarter(60) == 60

    def test_over_60_minutes(self):
        """Test rounding for durations over 1 hour"""
        assert round_quarter(61) == 75
        assert round_quarter(90) == 90
        assert round_quarter(91) == 105
        assert round_quarter(120) == 120

    def test_zero_and_negative(self):
        """Zero and negative values should return 0"""
        assert round_quarter(0) == 0
        assert round_quarter(-10) == 0


class TestMinutesToHours:
    """Test conversion from minutes to decimal hours"""

    def test_basic_conversion(self):
        """Test basic minute to hour conversion"""
        assert minutes_to_hours(60) == 1.0
        assert minutes_to_hours(30) == 0.5
        assert minutes_to_hours(90) == 1.5

    def test_quarter_hours(self):
        """Test 15-minute increments"""
        assert minutes_to_hours(15) == 0.25
        assert minutes_to_hours(45) == 0.75

    def test_zero(self):
        """Test zero minutes"""
        assert minutes_to_hours(0) == 0.0


class TestSummarizeByTaskDay:
    """Test daily task summary with rounding"""

    def test_single_entry(self):
        """Test summarizing a single work entry"""
        entries = [
            {"task_id": 1, "date": date(2024, 1, 8), "minutes": 42}
        ]
        result = summarize_by_task_day(entries)

        assert 1 in result
        assert result[1]["2024-01-08"] == 45  # rounded from 42
        assert result[1]["total"] == 45

    def test_multiple_entries_same_day(self):
        """Test multiple entries for same task/day (sum before rounding)"""
        entries = [
            {"task_id": 1, "date": date(2024, 1, 8), "minutes": 32},
            {"task_id": 1, "date": date(2024, 1, 8), "minutes": 10},
        ]
        result = summarize_by_task_day(entries)

        # 32 + 10 = 42, rounds to 45
        assert result[1]["2024-01-08"] == 45
        assert result[1]["total"] == 45

    def test_multiple_days(self):
        """Test entries across multiple days"""
        entries = [
            {"task_id": 1, "date": date(2024, 1, 8), "minutes": 60},
            {"task_id": 1, "date": date(2024, 1, 9), "minutes": 30},
        ]
        result = summarize_by_task_day(entries)

        assert result[1]["2024-01-08"] == 60
        assert result[1]["2024-01-09"] == 30
        assert result[1]["total"] == 90

    def test_multiple_tasks(self):
        """Test multiple different tasks"""
        entries = [
            {"task_id": 1, "date": date(2024, 1, 8), "minutes": 60},
            {"task_id": 2, "date": date(2024, 1, 8), "minutes": 30},
        ]
        result = summarize_by_task_day(entries)

        assert 1 in result
        assert 2 in result
        assert result[1]["total"] == 60
        assert result[2]["total"] == 30

    def test_empty_entries(self):
        """Test with no entries"""
        result = summarize_by_task_day([])
        assert result == {}


class TestSummarizeByProject:
    """Test project summary with task breakdown"""

    def test_single_project_single_task(self):
        """Test basic project/task summary"""
        entries = [
            {"task_id": 1, "date": date(2024, 1, 8), "minutes": 60}  # Monday
        ]
        tasks = [
            {"id": 1, "title": "Task 1", "project_id": 1}
        ]
        projects = {1: "Project A"}

        result = summarize_by_project(entries, tasks, projects)

        assert "Project A" in result
        assert "Task 1" in result["Project A"]
        assert result["Project A"]["Task 1"]["Mon"] == 1.0  # 60 min = 1 hour
        assert result["Project A"]["Task 1"]["Total"] == 1.0

    def test_task_without_project(self):
        """Test task with no project assigned"""
        entries = [
            {"task_id": 1, "date": date(2024, 1, 8), "minutes": 30}
        ]
        tasks = [
            {"id": 1, "title": "Personal Task", "project_id": None}
        ]
        projects = {}

        result = summarize_by_project(entries, tasks, projects)

        assert "No Project" in result
        assert "Personal Task" in result["No Project"]

    def test_multiple_days_week(self):
        """Test entries across the week"""
        entries = [
            {"task_id": 1, "date": date(2024, 1, 8), "minutes": 60},   # Mon
            {"task_id": 1, "date": date(2024, 1, 9), "minutes": 45},   # Tue
            {"task_id": 1, "date": date(2024, 1, 10), "minutes": 30},  # Wed
        ]
        tasks = [
            {"id": 1, "title": "Development", "project_id": 1}
        ]
        projects = {1: "Client Work"}

        result = summarize_by_project(entries, tasks, projects)

        task_data = result["Client Work"]["Development"]
        assert task_data["Mon"] == 1.0
        assert task_data["Tue"] == 0.75
        assert task_data["Wed"] == 0.5
        assert task_data["Total"] == 2.25

    def test_empty_entries(self):
        """Test with no entries"""
        result = summarize_by_project([], [], {})
        assert result == {}


# Run tests with: pytest tests/test_time_engine.py -v
