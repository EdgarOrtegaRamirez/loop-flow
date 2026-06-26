"""CLI commands for LoopFlow."""

from __future__ import annotations

import textwrap
from collections import Counter
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from loopflow.loop_detection import LoopDetector
from loopflow.models import AgentType, Iteration, LoopSeverity
from loopflow.storage import Storage

console = Console()


def _get_storage(ctx) -> Storage:
    """Get storage from CLI context."""
    return ctx.ensure_object(dict).get("storage") or Storage()


@click.group()
@click.option("--db", "db_path", default=None, help="Path to SQLite database file")
@click.pass_context
def main(ctx, db_path):
    """LoopFlow — AI agent iteration tracker and loop detector.

    Track your AI coding sessions, detect unproductive loops, and get actionable suggestions.
    """
    ctx.ensure_object(dict)
    ctx.obj["storage"] = Storage(db_path)


@main.command()
@click.argument("session_id")
@click.argument("prompt")
@click.option("--agent", "agent_type", default="manual", type=click.Choice([a.value for a in AgentType]), help="Agent type")
@click.option("--files", "files_changed", default="", help="Comma-separated list of files changed")
@click.option("--error", default=None, help="Error message, if any")
@click.option("--success/--failure", default=True, help="Whether iteration succeeded")
@click.option("--tokens", default=None, type=int, help="Estimated tokens used")
@click.option("--duration", default=None, type=float, help="Duration in seconds")
@click.option("--notes", default=None, help="Additional notes")
@click.pass_context
def add(ctx, session_id, prompt, agent_type, files_changed, error, success, tokens, duration, notes):
    """Add a new iteration to a session.

    SESSION_ID: Unique identifier for this session.
    PROMPT: The prompt or instruction given to the AI agent.
    """
    storage = _get_storage(ctx)

    files = [f.strip() for f in files_changed.split(",") if f.strip()] if files_changed else []

    iteration = Iteration(
        session_id=session_id,
        agent_type=AgentType(agent_type),
        prompt=prompt,
        files_changed=files,
        error_message=error,
        success=success,
        tokens_used=tokens,
        duration_seconds=duration,
        notes=notes,
    )

    storage.add_iteration(iteration)
    console.print(f"[green]✓[/green] Added iteration to session [bold]{session_id}[/bold]")


@main.command()
@click.argument("session_id", default=None, required=False)
@click.option("--limit", "-n", default=20, type=int, help="Number of iterations to show")
@click.pass_context
def list(ctx, session_id, limit):
    """List recent iterations, optionally filtered by session."""
    storage = _get_storage(ctx)
    iterations = storage.get_iterations(session_id=session_id, limit=limit)

    if not iterations:
        console.print("[yellow]No iterations found.[/yellow]")
        return

    table = Table(title=f"Iterations{' — Session: ' + session_id if session_id else ''}")
    table.add_column("Time", style="dim", width=20)
    table.add_column("Status", width=6)
    table.add_column("Agent", width=12)
    table.add_column("Prompt", max_width=50)
    table.add_column("Files", max_width=30)
    table.add_column("Error", max_width=30)

    for iteration in iterations:
        status = "[green]✓[/green]" if iteration.success else "[red]✗[/red]"
        files = ", ".join(iteration.files_changed[:2])
        if len(iteration.files_changed) > 2:
            files += f" +{len(iteration.files_changed) - 2}"
        error = iteration.error_message.split("\n")[0][:30] if iteration.error_message else ""

        table.add_row(
            datetime.fromisoformat(iteration.timestamp).strftime("%H:%M:%S"),
            status,
            iteration.agent_type.value,
            iteration.prompt[:48] + "..." if len(iteration.prompt) > 48 else iteration.prompt,
            files or "-",
            error or "-",
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(iterations)} of {len(storage.get_iterations(session_id=session_id, limit=9999))} iterations[/dim]")


@main.command()
@click.argument("session_id", default=None, required=False)
@click.option("--window", "-w", default=None, type=int, help="Only analyze last N iterations")
@click.pass_context
def check(ctx, session_id, window):
    """Check for loops in iterations."""
    storage = _get_storage(ctx)
    iterations = storage.get_iterations(session_id=session_id, limit=100)

    if not iterations:
        console.print("[yellow]No iterations to analyze.[/yellow]")
        return

    detector = LoopDetector()
    result = detector.detect_loops(iterations, window=window)

    # Score indicator
    if result.severity == LoopSeverity.CRITICAL:
        score_color = "red"
        score_icon = "🔴"
    elif result.severity == LoopSeverity.HIGH:
        score_color = "red"
        score_icon = "🟠"
    elif result.severity == LoopSeverity.MEDIUM:
        score_color = "yellow"
        score_icon = "🟡"
    else:
        score_color = "green"
        score_icon = "🟢"

    console.print(Panel(
        f"[bold]{score_icon} Loop Score: {result.score:.0f}/100[/bold]",
        title="Loop Detection Result",
        border_style=score_color,
    ))

    if result.is_loop:
        console.print(f"\n[bold red]⚠ Loop detected![/bold red]")
        console.print(f"  Type: {result.loop_type}")
        console.print(f"  Iterations analyzed: {result.iteration_count}")
        if result.repeated_files:
            console.print(f"  Repeated files: {', '.join(result.repeated_files)}")
        if result.repeated_errors:
            console.print(f"  Repeated errors: {result.repeated_errors[0][:60]}...")
    else:
        console.print(f"\n[bold green]✓ No loop detected.[/bold green]")
        console.print(f"  Iterations analyzed: {result.iteration_count}")

    # Suggestions
    if result.suggestions:
        console.print("\n[bold]Suggestions:[/bold]")
        for s in result.suggestions:
            console.print(f"  • {s}")


@main.command()
@click.argument("session_id", default=None, required=False)
@click.pass_context
def stats(ctx, session_id):
    """Show session statistics."""
    storage = _get_storage(ctx)

    if session_id:
        iterations = storage.get_iterations(session_id=session_id, limit=9999)
        title = f"Session: {session_id}"
    else:
        iterations = storage.get_iterations(limit=9999)
        title = "All Sessions"

    if not iterations:
        console.print("[yellow]No data to show.[/yellow]")
        return

    total = len(iterations)
    successful = sum(1 for i in iterations if i.success)
    failed = total - successful
    success_rate = (successful / total * 100) if total > 0 else 0

    # Files changed
    all_files = []
    for i in iterations:
        all_files.extend(i.files_changed)
    file_counts = sorted(Counter(all_files).items(), key=lambda x: -x[1])

    # Agent types
    agent_counts = Counter(i.agent_type.value for i in iterations)

    # Duration stats
    durations = [i.duration_seconds for i in iterations if i.duration_seconds is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0
    total_duration = sum(durations) if durations else 0

    # Token stats
    tokens = [i.tokens_used for i in iterations if i.tokens_used is not None]
    total_tokens = sum(tokens) if tokens else 0

    table = Table(title=title)
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Total iterations", str(total))
    table.add_row("Successful", f"[green]{successful}[/green]")
    table.add_row("Failed", f"[red]{failed}[/red]")
    table.add_row("Success rate", f"{success_rate:.1f}%")
    table.add_row("Avg duration", f"{avg_duration:.1f}s" if avg_duration else "N/A")
    table.add_row("Total duration", f"{total_duration:.0f}s" if total_duration else "N/A")
    table.add_row("Total tokens", f"{total_tokens:,}" if total_tokens else "N/A")

    console.print(table)

    if file_counts:
        console.print("\n[bold]Most edited files:[/bold]")
        for f, c in file_counts[:10]:
            console.print(f"  {f}: {c}x")

    if agent_counts:
        console.print("\n[bold]By agent:[/bold]")
        for agent, count in agent_counts.most_common():
            console.print(f"  {agent}: {count}")


@main.command()
@click.argument("session_id")
@click.pass_context
def clear(ctx, session_id):
    """Delete all iterations for a session."""
    storage = _get_storage(ctx)
    deleted = storage.delete_session(session_id)
    console.print(f"[green]✓[/green] Deleted {deleted} iterations from session [bold]{session_id}[/bold]")


@main.command()
@click.pass_context
def sessions(ctx):
    """List all session IDs."""
    storage = _get_storage(ctx)
    session_ids = storage.get_session_ids()

    if not session_ids:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    console.print(f"[bold]Sessions ({len(session_ids)}):[/bold]")
    for sid in session_ids:
        iterations = storage.get_iterations(session_id=sid, limit=1)
        count = len(storage.get_iterations(session_id=sid, limit=9999))
        console.print(f"  [cyan]{sid}[/cyan] ({count} iterations)")


@main.command()
def sample_config():
    """Print a sample configuration for LoopFlow."""
    config = textwrap.dedent("""\
        # LoopFlow Configuration
        # Place this in ~/.config/loopflow/config.yaml

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
    """)
    console.print(config)


@main.command()
def version():
    """Show LoopFlow version."""
    from loopflow import __version__
    console.print(f"LoopFlow v{__version__}")


if __name__ == "__main__":
    main()
