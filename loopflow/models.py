"""Pydantic models for LoopFlow data structures."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Supported AI coding agent types."""
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    COPILOT = "copilot"
    MANUAL = "manual"
    CUSTOM = "custom"


class LoopSeverity(str, Enum):
    """Severity levels for detected loops."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Iteration(BaseModel):
    """A single iteration in an AI coding session."""
    id: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: str = Field(description="Unique session identifier")
    agent_type: AgentType = Field(default=AgentType.MANUAL)
    prompt: str = Field(default="", description="The prompt or instruction given")
    files_changed: list[str] = Field(default_factory=list, description="Files modified in this iteration")
    error_message: Optional[str] = Field(default=None, description="Error encountered, if any")
    success: bool = Field(default=True, description="Whether the iteration succeeded")
    tokens_used: Optional[int] = Field(default=None, description="Estimated tokens used")
    duration_seconds: Optional[float] = Field(default=None, description="Duration of this iteration")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: Optional[str] = Field(default=None)

    def to_log_line(self) -> str:
        """Format iteration as a human-readable log line."""
        status = "✓" if self.success else "✗"
        files = ", ".join(self.files_changed[:3])
        if len(self.files_changed) > 3:
            files += f" (+{len(self.files_changed) - 3} more)"
        return f"[{self.timestamp}] {status} {self.agent_type.value}: {self.prompt[:60]}... | files: {files}"


class LoopDetection(BaseModel):
    """Result of a loop detection analysis."""
    is_loop: bool = Field(description="Whether a loop was detected")
    severity: LoopSeverity = Field(description="Severity of the loop")
    score: float = Field(ge=0.0, le=100.0, description="Loop score 0-100")
    loop_type: str = Field(description="Type of loop detected")
    repeated_files: list[str] = Field(default_factory=list, description="Files being repeatedly edited")
    repeated_errors: list[str] = Field(default_factory=list, description="Errors occurring repeatedly")
    iteration_count: int = Field(description="Number of iterations in the loop")
    suggestions: list[str] = Field(default_factory=list, description="Actionable suggestions to break the loop")

    @property
    def needs_attention(self) -> bool:
        return self.severity in (LoopSeverity.HIGH, LoopSeverity.CRITICAL)
