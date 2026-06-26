# LoopFlow

AI agent iteration tracker and loop detector for coding workflows.

Track your AI coding sessions, detect unproductive loops, and get actionable suggestions to break free.

## Why LoopFlow?

When using AI coding assistants (Claude Code, Cursor, Copilot), it's easy to get stuck in unproductive loops:
- Repeatedly editing the same file with the same error
- Running the same failing test over and over
- Making small changes that don't accumulate into progress

LoopFlow detects these patterns and gives you a **loop score** (0-100) with actionable suggestions.

## Features

- **SQLite-backed storage** — persistent, local-first, no cloud dependencies
- **Loop detection engine** — analyzes iteration patterns (repeated edits, recurring errors, failure rates)
- **Loop scoring** — 0-100 scale with severity levels (low, medium, high, critical)
- **Multiple agent types** — supports Claude Code, Cursor, GitHub Copilot, manual, and custom agents
- **Rich CLI** — table output, session filtering, statistics
- **Extensible** — easy to add new detection heuristics and agent integrations

## Installation

```bash
pip install loop-flow
```

Or install from source:

```bash
git clone https://github.com/EdgarOrtegaRamirez/loop-flow.git
cd loop-flow
pip install -e .
```

## Quick Start

### Record an iteration

```bash
loop-flow add my-session "Fix the login bug" \
  --agent claude-code \
  --files "src/auth.py,tests/test_auth.py" \
  --tokens 2000 \
  --duration 120
```

### Check for loops

```bash
loop-flow check my-session
```

### View iterations

```bash
loop-flow list my-session
loop-flow list my-session -n 10
```

### View statistics

```bash
loop-flow stats my-session
```

### List all sessions

```bash
loop-flow sessions
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `add <session> <prompt>` | Add a new iteration |
| `list [session]` | List recent iterations |
| `check [session]` | Check for loops |
| `stats [session]` | Show session statistics |
| `clear <session>` | Delete a session |
| `sessions` | List all sessions |
| `sample-config` | Print sample config |
| `version` | Show version |

### `add` Options

| Option | Description |
|--------|-------------|
| `--agent` | Agent type: `claude-code`, `cursor`, `copilot`, `manual`, `custom` |
| `--files` | Comma-separated list of files changed |
| `--error` | Error message (if iteration failed) |
| `--success` / `--failure` | Whether iteration succeeded |
| `--tokens` | Estimated tokens used |
| `--duration` | Duration in seconds |
| `--notes` | Additional notes |

## Loop Detection

LoopFlow uses a scoring algorithm based on several heuristics:

| Signal | Score | Description |
|--------|-------|-------------|
| Repeated file edits | 15/file | Same file edited 2+ times per iteration window |
| Repeated errors | 20/error | Same error message appearing 2+ times |
| High failure rate | 20 | More than 50% of iterations failed |
| Rapid iterations | 10 | Average duration under 5 seconds across 5+ iterations |

### Severity Levels

- 🟢 **Low** (0-10): No significant loop detected
- 🟡 **Medium** (10-30): Minor repetitive patterns
- 🔴 **High** (60-79): Clear unproductive loop detected
- 🔴 **Critical** (80+): Severe loop — immediate intervention recommended

## Programmatic Usage

```python
from loopflow.models import Iteration, AgentType
from loopflow.storage import Storage
from loopflow.loop_detection import LoopDetector

# Storage
with Storage() as db:
    # Add an iteration
    iteration = Iteration(
        session_id="my-session",
        agent_type=AgentType.CLAUDE_CODE,
        prompt="Fix the login bug",
        files_changed=["src/auth.py"],
        success=False,
        error_message="TypeError: Cannot read property 'user' of null",
        tokens_used=1500,
    )
    db.add_iteration(iteration)

    # Detect loops
    iterations = db.get_iterations(session_id="my-session")
    detector = LoopDetector()
    result = detector.detect_loops(iterations)

    if result.is_loop:
        print(f"Loop detected! Score: {result.score}/100")
        print(f"Suggestions: {result.suggestions}")
```

## Configuration

```yaml
# ~/.config/loopflow/config.yaml
database:
  path: ~/.loopflow/loopflow.db

detection:
  file_repeat_threshold: 2
  error_repeat_threshold: 2
  min_iterations: 3
  high_score_threshold: 60
  critical_score_threshold: 80

output:
  color: true
  show_suggestions: true
```

## Architecture

```
loopflow/
├── models.py          # Pydantic models (Iteration, LoopDetection)
├── storage.py         # SQLite-backed storage layer
├── loop_detection/
│   └── engine.py      # Loop detection algorithm
├── cli/
│   └── main.py        # CLI commands (click-based)
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=loopflow --cov-report=term-missing
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Related Projects

- [SessionLens](https://github.com/EdgarOrtegaRamirez/session-lens) — AI coding session analyzer and optimizer
- [MemoryPipe](https://github.com/EdgarOrtegaRamirez/memory-pipe) — AI agent memory and context persistence
- [Context Router](https://github.com/EdgarOrtegaRamirez/context-router) — Smart AI request router
