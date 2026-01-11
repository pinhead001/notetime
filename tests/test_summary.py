"""
Tests for summary.py - Day 4 Weekly Summary Generator

Run with: pytest tests/test_summary.py -v
"""
import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from notetime.models import Base, Week, Project, Task, WorkEntry
from notetime.summary import (
    generate_weekly_summary,
    get_weekly_totals,
    format_summary_text
)


@pytest.fixture
def session():
    """Create in-memory database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_week(session):
    """Create a sample week with projects and tasks"""
    week = Week(start_date=date(2024, 1, 8))  # Monday
    session.add(week)
    session.flush()
    return week


@pytest.fixture
def sample_projects(session):
    """Create sample projects"""
    project1 = Project(name="Client Work")
    project2 = Project(name="Internal")
    session.add(project1)
    session.add(project2)
    session.flush()
    return {"client": project1, "internal": project2}


class TestGenerateWeeklySummary:
    """Test generate_weekly_summary function"""

    def test_empty_week(self, session, sample_week):
        """Test summary for week with no work entries"""
        summary = generate_weekly_summary(sample_week.id, session)
        assert summary == {}

    def test_week_with_tasks_no_entries(self, session, sample_week, sample_projects):
        """Test week with tasks but no work entries"""
        task = Task(
            title="Test Task",
            week_id=sample_week.id,
            project_id=sample_projects["client"].id
        )
        session.add(task)
        session.commit()

        summary = generate_weekly_summary(sample_week.id, session)
        assert summary == {}

    def test_single_project_single_task(self, session, sample_week, sample_projects):
        """Test basic summary with one project and task"""
        task = Task(
            title="Development",
            week_id=sample_week.id,
            project_id=sample_projects["client"].id
        )
        session.add(task)
        session.flush()

        # Add work entry for Monday (60 minutes = 1 hour)
        entry = WorkEntry(
            task_id=task.id,
            date=date(2024, 1, 8),  # Monday
            minutes=60
        )
        session.add(entry)
        session.commit()

        summary = generate_weekly_summary(sample_week.id, session)

        assert "Client Work" in summary
        assert "Development" in summary["Client Work"]
        assert summary["Client Work"]["Development"]["Mon"] == 1.0
        assert summary["Client Work"]["Development"]["Total"] == 1.0

    def test_multiple_entries_same_day(self, session, sample_week, sample_projects):
        """Test multiple work entries on same day (should sum and round)"""
        task = Task(
            title="Development",
            week_id=sample_week.id,
            project_id=sample_projects["client"].id
        )
        session.add(task)
        session.flush()

        # Add two entries on Monday: 32 + 10 = 42 minutes -> rounds to 45
        session.add(WorkEntry(task_id=task.id, date=date(2024, 1, 8), minutes=32))
        session.add(WorkEntry(task_id=task.id, date=date(2024, 1, 8), minutes=10))
        session.commit()

        summary = generate_weekly_summary(sample_week.id, session)

        # 42 minutes rounds to 45 minutes = 0.75 hours
        assert summary["Client Work"]["Development"]["Mon"] == 0.75

    def test_multiple_days(self, session, sample_week, sample_projects):
        """Test work entries across multiple days"""
        task = Task(
            title="Development",
            week_id=sample_week.id,
            project_id=sample_projects["client"].id
        )
        session.add(task)
        session.flush()

        # Monday: 60 min, Tuesday: 90 min, Friday: 30 min
        session.add(WorkEntry(task_id=task.id, date=date(2024, 1, 8), minutes=60))   # Mon
        session.add(WorkEntry(task_id=task.id, date=date(2024, 1, 9), minutes=90))   # Tue
        session.add(WorkEntry(task_id=task.id, date=date(2024, 1, 12), minutes=30))  # Fri
        session.commit()

        summary = generate_weekly_summary(sample_week.id, session)

        dev_data = summary["Client Work"]["Development"]
        assert dev_data["Mon"] == 1.0   # 60 min
        assert dev_data["Tue"] == 1.5   # 90 min
        assert dev_data["Fri"] == 0.5   # 30 min
        assert dev_data["Total"] == 3.0

    def test_multiple_tasks_multiple_projects(self, session, sample_week, sample_projects):
        """Test complex scenario with multiple projects and tasks"""
        # Client Work tasks
        task1 = Task(
            title="Development",
            week_id=sample_week.id,
            project_id=sample_projects["client"].id
        )
        task2 = Task(
            title="Code Review",
            week_id=sample_week.id,
            project_id=sample_projects["client"].id
        )

        # Internal project task
        task3 = Task(
            title="Documentation",
            week_id=sample_week.id,
            project_id=sample_projects["internal"].id
        )

        session.add_all([task1, task2, task3])
        session.flush()

        # Add work entries
        session.add(WorkEntry(task_id=task1.id, date=date(2024, 1, 8), minutes=120))  # Dev: 2h Mon
        session.add(WorkEntry(task_id=task2.id, date=date(2024, 1, 8), minutes=30))   # Review: 30m Mon
        session.add(WorkEntry(task_id=task1.id, date=date(2024, 1, 9), minutes=180))  # Dev: 3h Tue
        session.add(WorkEntry(task_id=task3.id, date=date(2024, 1, 9), minutes=60))   # Docs: 1h Tue
        session.commit()

        summary = generate_weekly_summary(sample_week.id, session)

        # Check Client Work
        assert "Client Work" in summary
        assert summary["Client Work"]["Development"]["Mon"] == 2.0
        assert summary["Client Work"]["Development"]["Tue"] == 3.0
        assert summary["Client Work"]["Development"]["Total"] == 5.0
        assert summary["Client Work"]["Code Review"]["Mon"] == 0.5

        # Check Internal
        assert "Internal" in summary
        assert summary["Internal"]["Documentation"]["Tue"] == 1.0

    def test_task_without_project(self, session, sample_week):
        """Test task with no project assigned"""
        task = Task(
            title="Personal Research",
            week_id=sample_week.id,
            project_id=None
        )
        session.add(task)
        session.flush()

        session.add(WorkEntry(task_id=task.id, date=date(2024, 1, 8), minutes=90))
        session.commit()

        summary = generate_weekly_summary(sample_week.id, session)

        assert "No Project" in summary
        assert summary["No Project"]["Personal Research"]["Mon"] == 1.5

    def test_nonexistent_week(self, session):
        """Test with invalid week ID"""
        summary = generate_weekly_summary(999, session)
        assert summary == {}


class TestGetWeeklyTotals:
    """Test get_weekly_totals function"""

    def test_empty_summary(self):
        """Test totals for empty summary"""
        totals = get_weekly_totals({})
        assert totals["Total"] == 0.0

    def test_single_project(self):
        """Test totals with one project"""
        summary = {
            "Client Work": {
                "Development": {"Mon": 2.0, "Tue": 3.0, "Total": 5.0}
            }
        }
        totals = get_weekly_totals(summary)

        assert totals["Client Work"] == 5.0
        assert totals["Total"] == 5.0

    def test_multiple_projects(self):
        """Test totals with multiple projects"""
        summary = {
            "Client Work": {
                "Development": {"Mon": 2.0, "Total": 2.0},
                "Review": {"Tue": 1.0, "Total": 1.0}
            },
            "Internal": {
                "Documentation": {"Wed": 3.0, "Total": 3.0}
            }
        }
        totals = get_weekly_totals(summary)

        assert totals["Client Work"] == 3.0  # 2.0 + 1.0
        assert totals["Internal"] == 3.0
        assert totals["Total"] == 6.0


class TestFormatSummaryText:
    """Test format_summary_text function"""

    def test_empty_summary(self):
        """Test formatting empty summary"""
        text = format_summary_text({})
        assert "No time logged" in text

    def test_formatted_output(self):
        """Test text formatting with data"""
        summary = {
            "Client Work": {
                "Development": {"Mon": 2.5, "Tue": 1.25, "Total": 3.75}
            }
        }
        text = format_summary_text(summary)

        assert "Client Work" in text
        assert "Development" in text
        assert "Mon 2.50h" in text
        assert "Tue 1.25h" in text
        assert "Total: 3.75h" in text

    def test_multiple_projects_formatting(self):
        """Test formatting with multiple projects"""
        summary = {
            "Client Work": {
                "Development": {"Mon": 2.0, "Total": 2.0}
            },
            "Internal": {
                "Documentation": {"Wed": 1.5, "Total": 1.5}
            }
        }
        text = format_summary_text(summary)

        assert "Client Work" in text
        assert "Internal" in text
        assert "Week Total: 3.50h" in text


# Run with: pytest tests/test_summary.py -v
