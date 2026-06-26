# LoopFlow — Notes for AI Agents

## Project Overview
LoopFlow is a CLI tool and Python library for tracking AI coding agent iterations and detecting unproductive loops.

## Architecture
- `loopflow/models.py` — Pydantic data models (Iteration, LoopDetection, AgentType, LoopSeverity)
- `loopflow/storage.py` — SQLite-backed storage with WAL mode
- `loopflow/loop_detection/engine.py` — Loop detection scoring algorithm
- `loopflow/cli/main.py` — Click-based CLI with 8 commands

## Key Design Decisions
- SQLite with WAL mode for concurrent read safety
- Pydantic v2 for data validation
- Click for CLI framework
- Rich for terminal rendering
- Scoring is heuristic-based, not ML-driven (keeps it lightweight and transparent)

## Loop Detection Algorithm
Score components:
1. Repeated file edits: 15 points per file edited 2+ times (max 40)
2. Repeated errors: 20 points per error occurring 2+ times (max 40)
3. High failure rate: 20 points if >50% iterations failed
4. Rapid iterations: 10 points if avg duration <5s across 5+ iterations
5. Total capped at 100

## Adding New Detection Signals
Add a new method in `LoopDetector.detect_loops()` that:
1. Computes a score contribution
2. Adds to the `score` variable
3. Updates `loop_type` and `suggestions`
4. Scores are additive, capped at 100

## Testing
- `pytest tests/ -v` — all tests
- `pytest tests/test_models.py` — model tests
- `pytest tests/test_storage.py` — storage tests
- `pytest tests/test_loop_detection.py` — detection algorithm tests
- `pytest tests/test_cli.py` — CLI integration tests

## Common Tasks
- Adding a new CLI command: add a `@main.command()` decorated function in `cli/main.py`
- Adding a new agent type: add to `AgentType` enum in `models.py`
- Changing detection thresholds: edit class constants in `loop_detection/engine.py`
