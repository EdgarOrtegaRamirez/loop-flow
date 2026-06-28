"""Tests for LoopFlow CLI."""

import pytest
from click.testing import CliRunner

from loopflow.cli.main import main


@pytest.fixture
def runner():
    """Create a Click CliRunner."""
    return CliRunner()


class TestCLI:
    """Tests for the CLI interface."""

    def test_version(self, runner):
        """Test version command."""
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "LoopFlow" in result.output

    def test_help(self, runner):
        """Test help output."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "LoopFlow" in result.output
        assert "add" in result.output
        assert "list" in result.output
        assert "check" in result.output
        assert "stats" in result.output

    def test_sample_config(self, runner):
        """Test sample-config command."""
        result = runner.invoke(main, ["sample-config"])
        assert result.exit_code == 0
        assert "LoopFlow Configuration" in result.output

    def test_add_iteration(self, runner, tmp_path):
        """Test adding an iteration."""
        db = str(tmp_path / "test.db")
        result = runner.invoke(
            main,
            ["--db", db, "add", "test-session", "Fix the bug",
             "--agent", "claude-code", "--files", "main.py",
             "--success", "--tokens", "1000"],
        )
        assert result.exit_code == 0
        assert "Added iteration" in result.output

    def test_list_empty(self, runner, tmp_path):
        """Test listing when no iterations exist."""
        db = str(tmp_path / "test.db")
        result = runner.invoke(main, ["--db", db, "list"])
        assert result.exit_code == 0
        assert "No iterations found" in result.output

    def test_list_after_add(self, runner, tmp_path):
        """Test listing after adding iterations."""
        db = str(tmp_path / "test.db")
        runner.invoke(main, ["--db", db, "add", "test-session", "First prompt", "--files", "main.py"])
        runner.invoke(main, ["--db", db, "add", "test-session", "Second prompt", "--files", "utils.py"])
        result = runner.invoke(main, ["--db", db, "list", "test-session"])
        assert result.exit_code == 0
        assert "First" in result.output or "Second" in result.output

    def test_check_no_data(self, runner, tmp_path):
        """Test check command with no data."""
        db = str(tmp_path / "test.db")
        result = runner.invoke(main, ["--db", db, "check"])
        assert result.exit_code == 0
        assert "No iterations to analyze" in result.output

    def test_stats_no_data(self, runner, tmp_path):
        """Test stats command with no data."""
        db = str(tmp_path / "test.db")
        result = runner.invoke(main, ["--db", db, "stats"])
        assert result.exit_code == 0
        assert "No data to show" in result.output

    def test_clear_session(self, runner, tmp_path):
        """Test clearing a session."""
        db = str(tmp_path / "test.db")
        runner.invoke(main, ["--db", db, "add", "test-session", "Prompt", "--files", "main.py"])
        result = runner.invoke(main, ["--db", db, "clear", "test-session"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_sessions_empty(self, runner, tmp_path):
        """Test sessions command with no sessions."""
        db = str(tmp_path / "test.db")
        result = runner.invoke(main, ["--db", db, "sessions"])
        assert result.exit_code == 0
        assert "No sessions found" in result.output

    def test_check_with_loop_data(self, runner, tmp_path):
        """Test check command with loop-inducing data."""
        db = str(tmp_path / "test.db")
        for i in range(5):
            runner.invoke(
                main,
                ["--db", db, "add", "loop-session",
                 f"Fix attempt {i+1}", "--files", "main.py",
                 "--error", "Same error", "--failure"],
            )
        result = runner.invoke(main, ["--db", db, "check", "loop-session"])
        assert result.exit_code == 0
        assert "Loop" in result.output
