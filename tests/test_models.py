"""Tests for LoopFlow models."""

import pytest

from loopflow.models import AgentType, Iteration, LoopDetection, LoopSeverity


class TestAgentType:
    """Tests for the AgentType enum."""

    def test_enum_values(self):
        """Test that all agent types have correct string values."""
        assert AgentType.CLAUDE_CODE.value == "claude-code"
        assert AgentType.CURSOR.value == "cursor"
        assert AgentType.COPILOT.value == "copilot"
        assert AgentType.MANUAL.value == "manual"
        assert AgentType.CUSTOM.value == "custom"

    def test_from_string(self):
        """Test creating AgentType from string."""
        assert AgentType("claude-code") == AgentType.CLAUDE_CODE
        assert AgentType("cursor") == AgentType.CURSOR
        assert AgentType("manual") == AgentType.MANUAL

    def test_invalid_string(self):
        """Test that invalid string raises error."""
        with pytest.raises(ValueError):
            AgentType("invalid-agent")


class TestIteration:
    """Tests for the Iteration model."""

    def test_create_minimal(self):
        """Test creating an iteration with minimal fields."""
        iteration = Iteration(session_id="test-session")
        assert iteration.session_id == "test-session"
        assert iteration.agent_type == AgentType.MANUAL
        assert iteration.prompt == ""
        assert iteration.files_changed == []
        assert iteration.error_message is None
        assert iteration.success is True
        assert iteration.tokens_used is None
        assert iteration.duration_seconds is None
        assert iteration.timestamp is not None

    def test_create_full(self):
        """Test creating an iteration with all fields."""
        iteration = Iteration(
            session_id="test-session",
            agent_type=AgentType.CLAUDE_CODE,
            prompt="Fix the bug in main.py",
            files_changed=["main.py", "test_main.py"],
            error_message="AttributeError: 'NoneType' object has no attribute 'get'",
            success=False,
            tokens_used=1500,
            duration_seconds=120.5,
            notes="Tried to fix NoneType error",
        )
        assert iteration.session_id == "test-session"
        assert iteration.agent_type == AgentType.CLAUDE_CODE
        assert iteration.prompt == "Fix the bug in main.py"
        assert iteration.files_changed == ["main.py", "test_main.py"]
        assert iteration.error_message == "AttributeError: 'NoneType' object has no attribute 'get'"
        assert iteration.success is False
        assert iteration.tokens_used == 1500
        assert iteration.duration_seconds == 120.5
        assert iteration.notes == "Tried to fix NoneType error"

    def test_to_log_line(self):
        """Test formatting iteration as log line."""
        iteration = Iteration(
            session_id="test",
            agent_type=AgentType.CLAUDE_CODE,
            prompt="This is a very long prompt that should be truncated in the log line output",
            files_changed=["main.py", "utils.py", "config.py", "test_config.py", "docs/guide.md"],
            success=True,
        )
        log_line = iteration.to_log_line()
        assert iteration.timestamp in log_line
        assert "claude-code" in log_line
        assert "✓" in log_line
        assert "main.py" in log_line
        assert "utils.py" in log_line
        assert "+2 more" in log_line

    def test_to_log_line_failure(self):
        """Test log line for failed iteration."""
        iteration = Iteration(
            session_id="test",
            agent_type=AgentType.MANUAL,
            prompt="Debug the issue",
            files_changed=["main.py"],
            success=False,
        )
        log_line = iteration.to_log_line()
        assert "✗" in log_line

    def test_to_log_line_many_files(self):
        """Test log line with many files."""
        iteration = Iteration(
            session_id="test",
            prompt="Test",
            files_changed=["a.py", "b.py", "c.py", "d.py", "e.py"],
            success=True,
        )
        log_line = iteration.to_log_line()
        assert "+2 more" in log_line


class TestLoopDetection:
    """Tests for the LoopDetection model."""

    def test_create_detection(self):
        """Test creating a loop detection result."""
        detection = LoopDetection(
            is_loop=True,
            severity=LoopSeverity.HIGH,
            score=75.0,
            loop_type="repeated_file_edits",
            repeated_files=["main.py", "utils.py"],
            repeated_errors=["ModuleNotFoundError"],
            iteration_count=10,
            suggestions=["Step back and reassess"],
        )
        assert detection.is_loop is True
        assert detection.severity == LoopSeverity.HIGH
        assert detection.score == 75.0
        assert detection.loop_type == "repeated_file_edits"
        assert "main.py" in detection.repeated_files
        assert detection.iteration_count == 10
        assert "Step back and reassess" in detection.suggestions

    def test_needs_attention_high(self):
        """Test needs_attention for high severity."""
        detection = LoopDetection(
            is_loop=True,
            severity=LoopSeverity.HIGH,
            score=70.0,
            loop_type="test",
            iteration_count=5,
            suggestions=[],
        )
        assert detection.needs_attention is True

    def test_needs_attention_critical(self):
        """Test needs_attention for critical severity."""
        detection = LoopDetection(
            is_loop=True,
            severity=LoopSeverity.CRITICAL,
            score=90.0,
            loop_type="test",
            iteration_count=5,
            suggestions=[],
        )
        assert detection.needs_attention is True

    def test_needs_attention_medium(self):
        """Test needs_attention for medium severity (should be False)."""
        detection = LoopDetection(
            is_loop=False,
            severity=LoopSeverity.MEDIUM,
            score=30.0,
            loop_type="test",
            iteration_count=5,
            suggestions=[],
        )
        assert detection.needs_attention is False

    def test_needs_attention_low(self):
        """Test needs_attention for low severity."""
        detection = LoopDetection(
            is_loop=False,
            severity=LoopSeverity.LOW,
            score=0.0,
            loop_type="none",
            iteration_count=0,
            suggestions=[],
        )
        assert detection.needs_attention is False

    def test_score_capped(self):
        """Test that score stays within bounds."""
        detection = LoopDetection(
            is_loop=False,
            severity=LoopSeverity.LOW,
            score=50.0,
            loop_type="test",
            iteration_count=5,
            suggestions=[],
        )
        assert 0.0 <= detection.score <= 100.0
