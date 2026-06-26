"""Tests for LoopFlow storage."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from loopflow.models import AgentType, Iteration
from loopflow.storage import Storage


@pytest.fixture
def storage():
    """Create a temporary storage instance."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        s = Storage(db_path=db_path)
        yield s
    finally:
        s.close()
        os.unlink(db_path)


class TestStorage:
    """Tests for the Storage class."""

    def test_add_iteration(self, storage):
        """Test adding an iteration."""
        iteration = Iteration(
            session_id="test-session",
            agent_type=AgentType.CLAUDE_CODE,
            prompt="Fix the bug",
            files_changed=["main.py"],
            success=True,
        )
        iteration_id = storage.add_iteration(iteration)
        assert iteration_id == iteration.id

        # Verify it was stored
        retrieved = storage.get_iterations(session_id="test-session")
        assert len(retrieved) == 1
        assert retrieved[0].prompt == "Fix the bug"
        assert retrieved[0].agent_type == AgentType.CLAUDE_CODE

    def test_add_multiple_iterations(self, storage):
        """Test adding multiple iterations."""
        for i in range(5):
            iteration = Iteration(
                session_id="test-session",
                prompt=f"Attempt {i+1}",
                files_changed=["main.py"],
                success=i != 4,
            )
            storage.add_iteration(iteration)

        iterations = storage.get_iterations(session_id="test-session")
        assert len(iterations) == 5

    def test_get_iterations_order(self, storage):
        """Test that iterations are returned in reverse chronological order."""
        for i in range(3):
            iteration = Iteration(
                session_id="test-session",
                prompt=f"Iteration {i}",
                files_changed=["main.py"],
            )
            storage.add_iteration(iteration)

        iterations = storage.get_iterations(session_id="test-session")
        assert iterations[0].prompt == "Iteration 2"
        assert iterations[2].prompt == "Iteration 0"

    def test_get_iterations_limit(self, storage):
        """Test the limit parameter."""
        for i in range(10):
            iteration = Iteration(
                session_id="test-session",
                prompt=f"Iteration {i}",
            )
            storage.add_iteration(iteration)

        limited = storage.get_iterations(session_id="test-session", limit=3)
        assert len(limited) == 3

    def test_get_session_ids(self, storage):
        """Test getting all session IDs."""
        for session in ["session-a", "session-b", "session-a"]:
            iteration = Iteration(
                session_id=session,
                prompt="Test",
            )
            storage.add_iteration(iteration)

        session_ids = storage.get_session_ids()
        assert set(session_ids) == {"session-a", "session-b"}

    def test_delete_session(self, storage):
        """Test deleting a session."""
        for session in ["session-a", "session-b"]:
            for i in range(3):
                iteration = Iteration(
                    session_id=session,
                    prompt=f"Iteration {i}",
                )
                storage.add_iteration(iteration)

        deleted = storage.delete_session("session-a")
        assert deleted == 3

        remaining = storage.get_session_ids()
        assert remaining == ["session-b"]

    def test_clear_all(self, storage):
        """Test clearing all iterations."""
        for i in range(5):
            iteration = Iteration(
                session_id="test-session",
                prompt=f"Iteration {i}",
            )
            storage.add_iteration(iteration)

        deleted = storage.clear_all()
        assert deleted == 5
        assert len(storage.get_iterations()) == 0

    def test_context_manager(self):
        """Test using Storage as context manager."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            with Storage(db_path=db_path) as s:
                iteration = Iteration(session_id="test", prompt="Test")
                s.add_iteration(iteration)
            # Connection should be closed after context
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_default_db_path(self):
        """Test that default DB path is created in ~/.loopflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily override home for this test
            original_home = os.environ.get("HOME")
            os.environ["HOME"] = tmpdir
            try:
                s = Storage()
                assert ".loopflow" in s.db_path
                assert "loopflow.db" in s.db_path
                s.close()
            finally:
                if original_home:
                    os.environ["HOME"] = original_home

    def test_files_changed_serialization(self, storage):
        """Test that files_changed list is properly serialized/deserialized."""
        files = ["main.py", "utils/helper.py", "tests/test_main.py"]
        iteration = Iteration(
            session_id="test",
            prompt="Test",
            files_changed=files,
        )
        storage.add_iteration(iteration)
        retrieved = storage.get_iterations(session_id="test")
        assert retrieved[0].files_changed == files

    def test_error_message_none(self, storage):
        """Test storing iteration without error message."""
        iteration = Iteration(
            session_id="test",
            prompt="Test",
            error_message=None,
            success=True,
        )
        storage.add_iteration(iteration)
        retrieved = storage.get_iterations(session_id="test")
        assert retrieved[0].error_message is None
        assert retrieved[0].success is True

    def test_error_message_with_newlines(self, storage):
        """Test storing error message with newlines."""
        error = "Traceback (most recent call last):\n  File 'main.py', line 10\nValueError: test"
        iteration = Iteration(
            session_id="test",
            prompt="Test",
            error_message=error,
            success=False,
        )
        storage.add_iteration(iteration)
        retrieved = storage.get_iterations(session_id="test")
        assert retrieved[0].error_message == error
