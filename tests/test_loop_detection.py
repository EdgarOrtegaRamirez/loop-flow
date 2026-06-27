"""Tests for LoopFlow loop detection engine."""

import pytest

from loopflow.loop_detection.engine import LoopDetector
from loopflow.models import AgentType, Iteration, LoopSeverity


@pytest.fixture
def detector():
    return LoopDetector()


@pytest.fixture
def productive_iterations():
    """Create a list of productive iterations (no loop)."""
    files = [["main.py"], ["utils.py"], ["tests/test_main.py"], ["docs/readme.md"]]
    iterations = []
    for i, fs in enumerate(files):
        iterations.append(
            Iteration(
                session_id="productive",
                agent_type=AgentType.CLAUDE_CODE,
                prompt=f"Work on iteration {i+1}",
                files_changed=fs,
                success=True,
            )
        )
    return iterations


@pytest.fixture
def loop_iterations():
    """Create a list of iterations showing a clear loop."""
    iterations = []
    for i in range(5):
        iterations.append(
            Iteration(
                session_id="loop-session",
                agent_type=AgentType.CLAUDE_CODE,
                prompt=f"Try to fix the bug again (attempt {i+1})",
                files_changed=["main.py", "test_main.py"],
                error_message="AttributeError: 'NoneType' object has no attribute 'get'",
                success=False,
            )
        )
    return iterations


@pytest.fixture
def file_edit_loop_iterations():
    """Create iterations where the same file is edited repeatedly (without errors)."""
    iterations = []
    for i in range(5):
        iterations.append(
            Iteration(
                session_id="file-loop",
                agent_type=AgentType.CURSOR,
                prompt="Edit main.py again",
                files_changed=["main.py"],
                success=True,
            )
        )
    return iterations


class TestLoopDetector:
    """Tests for the LoopDetector class."""

    def test_no_loop_productive(self, detector, productive_iterations):
        """Test that productive iterations don't trigger loop detection."""
        result = detector.detect_loops(productive_iterations)
        assert result.is_loop is False
        assert result.score < 20.0
        assert result.severity == LoopSeverity.LOW

    def test_loop_detected_failed_retries(self, detector, loop_iterations):
        """Test detection of loop with repeated failures."""
        result = detector.detect_loops(loop_iterations)
        assert result.is_loop is True
        assert result.score >= 20.0
        assert result.severity in (LoopSeverity.HIGH, LoopSeverity.CRITICAL)
        assert len(result.repeated_errors) > 0
        assert result.repeated_errors[0] == "AttributeError: 'NoneType' object has no attribute 'get'"

    def test_file_edit_loop(self, detector, file_edit_loop_iterations):
        """Test detection of loop with repeated file edits."""
        result = detector.detect_loops(file_edit_loop_iterations)
        assert result.is_loop is True
        assert result.score >= 10.0
        assert "main.py" in result.repeated_files

    def test_insufficient_data(self, detector):
        """Test with fewer than min iterations."""
        iterations = [
            Iteration(session_id="test", prompt="First"),
            Iteration(session_id="test", prompt="Second"),
        ]
        result = detector.detect_loops(iterations)
        assert result.is_loop is False
        assert result.loop_type == "insufficient_data"
        assert result.score == 0.0

    def test_empty_iterations(self, detector):
        """Test with empty iteration list."""
        result = detector.detect_loops([])
        assert result.is_loop is False
        assert result.loop_type == "insufficient_data"
        assert result.score == 0.0

    def test_window_parameter(self, detector, loop_iterations):
        """Test that window parameter limits analysis."""
        # All 5 iterations should trigger loop detection
        result_full = detector.detect_loops(loop_iterations)
        assert result_full.is_loop is True

        # With window=2, should not trigger (insufficient data)
        result_windowed = detector.detect_loops(loop_iterations, window=2)
        assert result_windowed.loop_type == "insufficient_data"

    def test_score_capped_at_100(self, detector, loop_iterations):
        """Test that score is capped at 100."""
        result = detector.detect_loops(loop_iterations)
        assert result.score <= 100.0

    def test_severity_levels(self, detector):
        """Test that different loop patterns produce different severity levels."""
        # Heavy loop - many repeated files + errors + failures
        heavy_iterations = []
        for i in range(10):
            heavy_iterations.append(
                Iteration(
                    session_id="heavy-loop",
                    agent_type=AgentType.CLAUDE_CODE,
                    prompt=f"Fix attempt {i+1}",
                    files_changed=["main.py", "utils.py"],
                    error_message="Persistent error",
                    success=False,
                )
            )
        result = detector.detect_loops(heavy_iterations)
        assert result.severity in (LoopSeverity.HIGH, LoopSeverity.CRITICAL)

    def test_suggestions_present(self, detector, loop_iterations):
        """Test that suggestions are always present."""
        result = detector.detect_loops(loop_iterations)
        assert len(result.suggestions) > 0

    def test_suggestions_no_loop(self, detector, productive_iterations):
        """Test suggestions when no loop is detected."""
        result = detector.detect_loops(productive_iterations)
        assert len(result.suggestions) > 0

    def test_rapid_iteration_detection(self, detector):
        """Test detection of very rapid iterations (possible automated retry)."""
        iterations = []
        for i in range(6):
            iterations.append(
                Iteration(
                    session_id="rapid",
                    prompt=f"Iteration {i}",
                    files_changed=["main.py"],
                    duration_seconds=2.0,  # Very fast
                )
            )
        result = detector.detect_loops(iterations)
        # Rapid iterations alone shouldn't trigger a full loop, but should add to score
        assert result.score > 0
        # But shouldn't necessarily be a "loop" unless other indicators exist
        # The key is that rapid iterations are flagged

    def test_iteration_count_in_result(self, detector, loop_iterations):
        """Test that iteration count matches."""
        result = detector.detect_loops(loop_iterations)
        assert result.iteration_count == 5

    def test_mixed_success_failure(self, detector):
        """Test detection with mixed success/failure."""
        iterations = []
        for i in range(5):
            iterations.append(
                Iteration(
                    session_id="mixed",
                    prompt=f"Fix attempt {i+1}",
                    files_changed=["main.py"],
                    success=i % 2 == 0,
                    error_message="Some error" if i % 2 == 1 else None,
                )
            )
        result = detector.detect_loops(iterations)
        # Should detect some loop behavior
        assert result.iteration_count == 5

    def test_different_agent_types(self, detector):
        """Test that different agent types are handled."""
        iterations = []
        agents = [AgentType.CLAUDE_CODE, AgentType.CURSOR, AgentType.COPILOT]
        for i, agent in enumerate(agents):
            iterations.append(
                Iteration(
                    session_id="multi-agent",
                    agent_type=agent,
                    prompt=f"Attempt {i+1}",
                    files_changed=["main.py"],
                    success=False,
                    error_message="Same error",
                )
            )
        result = detector.detect_loops(iterations)
        assert result.iteration_count == 3
