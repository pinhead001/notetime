"""
Tests for rollover_week() function - Day 5 Rollover Engine

Run with: pytest tests/test_rollover.py -v
"""
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from notetime.models import Base, User, Week, Project, Task, TaskState
from notetime.time_engine import rollover_week


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
def test_user(session):
    """Create a test user for testing"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password_here"
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def two_weeks(session, test_user):
    """Create two consecutive weeks"""
    week1 = Week(start_date=date(2024, 1, 8), user_id=test_user.id)   # Week 1
    week2 = Week(start_date=date(2024, 1, 15), user_id=test_user.id)  # Week 2
    session.add_all([week1, week2])
    session.flush()
    return {"week1": week1, "week2": week2}


@pytest.fixture
def project(session, test_user):
    """Create a test project"""
    proj = Project(name="Test Project", user_id=test_user.id)
    session.add(proj)
    session.flush()
    return proj


class TestRolloverWeek:
    """Test rollover_week function"""

    def test_rollover_empty_week(self, session, two_weeks):
        """Test rollover with no tasks in source week"""
        counts = rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        assert counts["archived"] == 0
        assert counts["carried"] == 0
        assert counts["delegated"] == 0

    def test_rollover_active_tasks(self, session, two_weeks, project):
        """Test that ACTIVE tasks are carried over"""
        # Create active tasks in week 1
        task1 = Task(
            title="Active Task 1",
            week_id=two_weeks["week1"].id,
            state=TaskState.ACTIVE.value,
            project_id=project.id
        )
        task2 = Task(
            title="Active Task 2",
            week_id=two_weeks["week1"].id,
            state=TaskState.ACTIVE.value,
            priority=1
        )
        session.add_all([task1, task2])
        session.commit()

        # Rollover
        counts = rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        # Check counts
        assert counts["carried"] == 2
        assert counts["archived"] == 0
        assert counts["delegated"] == 0

        # Verify tasks were cloned to week 2
        from sqlalchemy import select
        week2_tasks = session.scalars(
            select(Task).where(Task.week_id == two_weeks["week2"].id)
        ).all()

        assert len(week2_tasks) == 2
        assert all(t.state == TaskState.ACTIVE.value for t in week2_tasks)

        # Verify original tasks still in week 1
        week1_tasks = session.scalars(
            select(Task).where(Task.week_id == two_weeks["week1"].id)
        ).all()
        assert len(week1_tasks) == 2

    def test_rollover_completed_tasks(self, session, two_weeks, project):
        """Test that COMPLETED tasks are archived (not carried)"""
        task = Task(
            title="Completed Task",
            week_id=two_weeks["week1"].id,
            state=TaskState.COMPLETED.value,
            project_id=project.id
        )
        session.add(task)
        session.commit()

        counts = rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        assert counts["archived"] == 1
        assert counts["carried"] == 0
        assert counts["delegated"] == 0

        # Verify no tasks in week 2
        from sqlalchemy import select
        week2_tasks = session.scalars(
            select(Task).where(Task.week_id == two_weeks["week2"].id)
        ).all()
        assert len(week2_tasks) == 0

    def test_rollover_canceled_tasks(self, session, two_weeks):
        """Test that CANCELED tasks are archived (not carried)"""
        task = Task(
            title="Canceled Task",
            week_id=two_weeks["week1"].id,
            state=TaskState.CANCELED.value
        )
        session.add(task)
        session.commit()

        counts = rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        assert counts["archived"] == 1
        assert counts["carried"] == 0
        assert counts["delegated"] == 0

    def test_rollover_delegated_tasks(self, session, two_weeks):
        """Test that DELEGATED tasks stay in old week (not carried)"""
        task = Task(
            title="Delegated Task",
            week_id=two_weeks["week1"].id,
            state=TaskState.DELEGATED.value,
            delegate="John Doe"
        )
        session.add(task)
        session.commit()

        counts = rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        assert counts["delegated"] == 1
        assert counts["carried"] == 0
        assert counts["archived"] == 0

        # Verify no tasks in week 2
        from sqlalchemy import select
        week2_tasks = session.scalars(
            select(Task).where(Task.week_id == two_weeks["week2"].id)
        ).all()
        assert len(week2_tasks) == 0

    def test_rollover_mixed_states(self, session, two_weeks, project):
        """Test rollover with tasks in different states"""
        tasks = [
            Task(title="Active 1", week_id=two_weeks["week1"].id, state=TaskState.ACTIVE.value),
            Task(title="Active 2", week_id=two_weeks["week1"].id, state=TaskState.ACTIVE.value),
            Task(title="Active 3", week_id=two_weeks["week1"].id, state=TaskState.ACTIVE.value),
            Task(title="Completed 1", week_id=two_weeks["week1"].id, state=TaskState.COMPLETED.value),
            Task(title="Completed 2", week_id=two_weeks["week1"].id, state=TaskState.COMPLETED.value),
            Task(title="Canceled", week_id=two_weeks["week1"].id, state=TaskState.CANCELED.value),
            Task(title="Delegated", week_id=two_weeks["week1"].id, state=TaskState.DELEGATED.value),
        ]
        session.add_all(tasks)
        session.commit()

        counts = rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        # Verify counts
        assert counts["carried"] == 3      # 3 active tasks
        assert counts["archived"] == 3     # 2 completed + 1 canceled
        assert counts["delegated"] == 1    # 1 delegated

        # Verify week 2 has only the active tasks
        from sqlalchemy import select
        week2_tasks = session.scalars(
            select(Task).where(Task.week_id == two_weeks["week2"].id)
        ).all()
        assert len(week2_tasks) == 3
        assert all(t.state == TaskState.ACTIVE.value for t in week2_tasks)

    def test_rollover_preserves_task_attributes(self, session, two_weeks, project):
        """Test that cloned tasks preserve title, priority, project_id"""
        task = Task(
            title="Important Feature",
            week_id=two_weeks["week1"].id,
            state=TaskState.ACTIVE.value,
            priority=1,
            project_id=project.id,
            delegate="Someone"
        )
        session.add(task)
        session.commit()

        rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        # Get the cloned task
        from sqlalchemy import select
        cloned_task = session.scalars(
            select(Task).where(Task.week_id == two_weeks["week2"].id)
        ).first()

        # Verify attributes
        assert cloned_task.title == "Important Feature"
        assert cloned_task.priority == 1
        assert cloned_task.project_id == project.id
        assert cloned_task.delegate == "Someone"
        assert cloned_task.state == TaskState.ACTIVE.value
        assert cloned_task.week_id == two_weeks["week2"].id

    def test_rollover_new_task_gets_new_id(self, session, two_weeks):
        """Test that cloned tasks get new IDs (not same as original)"""
        task = Task(
            title="Test Task",
            week_id=two_weeks["week1"].id,
            state=TaskState.ACTIVE.value
        )
        session.add(task)
        session.commit()
        original_id = task.id

        rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        # Get the cloned task
        from sqlalchemy import select
        cloned_task = session.scalars(
            select(Task).where(Task.week_id == two_weeks["week2"].id)
        ).first()

        # IDs should be different
        assert cloned_task.id != original_id
        assert cloned_task.id is not None

    def test_rollover_idempotent(self, session, two_weeks):
        """Test that running rollover twice doesn't double tasks"""
        task = Task(
            title="Test Task",
            week_id=two_weeks["week1"].id,
            state=TaskState.ACTIVE.value
        )
        session.add(task)
        session.commit()

        # First rollover
        counts1 = rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        # Second rollover (should carry from week 1 again, not week 2)
        counts2 = rollover_week(
            from_week_id=two_weeks["week1"].id,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        # Both should carry 1 task
        assert counts1["carried"] == 1
        assert counts2["carried"] == 1

        # Week 2 should have 2 tasks now (one from each rollover)
        from sqlalchemy import select
        week2_tasks = session.scalars(
            select(Task).where(Task.week_id == two_weeks["week2"].id)
        ).all()
        assert len(week2_tasks) == 2

    def test_rollover_nonexistent_week(self, session, two_weeks):
        """Test rollover from nonexistent week returns zero counts"""
        counts = rollover_week(
            from_week_id=999,
            to_week_id=two_weeks["week2"].id,
            session=session
        )

        assert counts["archived"] == 0
        assert counts["carried"] == 0
        assert counts["delegated"] == 0


# Run with: pytest tests/test_rollover.py -v
