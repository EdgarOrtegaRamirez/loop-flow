"""Tests for LoopFlow CLI."""

import subprocess
import sys

import pytest


def _run_cli(*args):
    """Run the loop-flow CLI with given arguments."""
    result = subprocess.run(
        [sys.executable, "-m", "loopflow.cli.main", *args],
        capture_output=True,
        text=True,
        cwd="/root/workspace/loop-flow",
    )
    return result


class TestCLI:
    """Tests for the CLI interface."""

    def test_version(self):
        """Test version command."""
        result = _run_cli("version")
        assert result.returncode == 0
        assert "LoopFlow" in result.stdout

    def test_help(self):
        """Test help output."""
        result = _run_cli("--help")
        assert result.returncode == 0
        assert "LoopFlow" in result.stdout
        assert "add" in result.stdout
        assert "list" in result.stdout
        assert "check" in result.stdout
        assert "stats" in result.stdout

    def test_sample_config(self):
        """Test sample-config command."""
        result = _run_cli("sample-config")
        assert result.returncode == 0
        assert "LoopFlow Configuration" in result.stdout

    def test_add_iteration(self, tmp_path):
        """Test adding an iteration."""
        db = str(tmp_path / "test.db")
        result = _run_cli(
            "--db", db,
            "add", "test-session", "Fix the bug",
            "--agent", "claude-code",
            "--files", "main.py",
            "--success",
            "--tokens", "1000",
        )
        assert result.returncode == 0
        assert "Added iteration" in result.stdout

    def test_list_empty(self, tmp_path):
        """Test listing when no iterations exist."""
        db = str(tmp_path / "test.db")
        result = _run_cli("--db", db, "list")
        assert result.returncode == 0
        assert "No iterations found" in result.stdout

    def test_list_after_add(self, tmp_path):
        """Test listing after adding iterations."""
        db = str(tmp_path / "test.db")
        _run_cli("--db", db, "add", "test-session", "First prompt", "--files", "main.py")
        _run_cli("--db", db, "add", "test-session", "Second prompt", "--files", "utils.py")
        result = _run_cli("--db", db, "list", "test-session")
        assert result.returncode == 0
        assert "First" in result.stdout or "Second" in result.stdout

    def test_check_no_data(self, tmp_path):
        """Test check command with no data."""
        db = str(tmp_path / "test.db")
        result = _run_cli("--db", db, "check")
        assert result.returncode == 0
        assert "No iterations to analyze" in result.stdout

    def test_stats_no_data(self, tmp_path):
        """Test stats command with no data."""
        db = str(tmp_path / "test.db")
        result = _run_cli("--db", db, "stats")
        assert result.returncode == 0
        assert "No data to show" in result.stdout

    def test_clear_session(self, tmp_path):
        """Test clearing a session."""
        db = str(tmp_path / "test.db")
        _run_cli("--db", db, "add", "test-session", "Prompt", "--files", "main.py")
        result = _run_cli("--db", db, "clear", "test-session")
        assert result.returncode == 0
        assert "Deleted" in result.stdout

    def test_sessions_empty(self, tmp_path):
        """Test sessions command with no sessions."""
        db = str(tmp_path / "test.db")
        result = _run_cli("--db", db, "sessions")
        assert result.returncode == 0
        assert "No sessions found" in result.stdout

    def test_check_with_loop_data(self, tmp_path):
        """Test check command with loop-inducing data."""
        db = str(tmp_path / "test.db")
        for i in range(5):
            _run_cli(
                "--db", db,
                "add", "loop-session",
                f"Fix attempt {i+1}",
                "--files", "main.py",
                "--error", "Same error",
                "--failure",
            )
        result = _run_cli("--db", db, "check", "loop-session")
        assert result.returncode == 0
        assert "Loop" in result.stdout
