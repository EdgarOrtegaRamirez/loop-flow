"""Loop detection engine — analyzes iterations to find unproductive loops."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from loopflow.models import Iteration, LoopDetection, LoopSeverity


class LoopDetector:
    """Analyzes iteration history to detect unproductive loops."""

    # Thresholds for loop detection
    FILE_REPEAT_THRESHOLD = 2  # Same file edited N+ times = suspicious
    ERROR_REPEAT_THRESHOLD = 2  # Same error N+ times = loop
    MIN_ITERATIONS_FOR_DETECTION = 3  # Need at least N iterations to detect
    HIGH_SCORE_THRESHOLD = 60
    CRITICAL_SCORE_THRESHOLD = 80
    LOOP_THRESHOLD = 10  # Score above this is considered a loop

    def detect_loops(
        self,
        iterations: list[Iteration],
        window: Optional[int] = None,
    ) -> LoopDetection:
        """Analyze iterations and return a loop detection result.

        Args:
            iterations: List of iterations to analyze.
            window: If set, only analyze the last N iterations.

        Returns:
            LoopDetection with analysis results.
        """
        if window:
            iterations = iterations[-window:]

        if len(iterations) < self.MIN_ITERATIONS_FOR_DETECTION:
            return LoopDetection(
                is_loop=False,
                severity=LoopSeverity.LOW,
                score=0.0,
                loop_type="insufficient_data",
                repeated_files=[],
                repeated_errors=[],
                iteration_count=len(iterations),
                suggestions=["Add more iterations for accurate detection."],
            )

        score = 0.0
        loop_type = "none"
        repeated_files: list[str] = []
        repeated_errors: list[str] = []
        suggestions: list[str] = []

        # Check for repeated file edits
        file_counts = Counter()
        for iteration in iterations:
            for f in iteration.files_changed:
                file_counts[f] += 1

        files_repeated = {f: c for f, c in file_counts.items() if c >= self.FILE_REPEAT_THRESHOLD}
        if files_repeated:
            repeated_files = list(files_repeated.keys())
            file_score = min(40.0, len(files_repeated) * 15.0)
            score += file_score
            loop_type = "repeated_file_edits"
            suggestions.append(
                f"Files repeatedly edited: {', '.join(repeated_files[:5])}. "
                "Consider stepping back to reassess your approach."
            )

        # Check for repeated errors
        error_counts = Counter()
        for iteration in iterations:
            if iteration.error_message:
                # Normalize error message (take first line, strip whitespace)
                normalized = iteration.error_message.split("\n")[0].strip()
                error_counts[normalized] += 1

        errors_repeated = {e: c for e, c in error_counts.items() if c >= self.ERROR_REPEAT_THRESHOLD}
        if errors_repeated:
            repeated_errors = list(errors_repeated.keys())
            error_score = min(40.0, len(errors_repeated) * 20.0)
            score += error_score
            if loop_type == "none":
                loop_type = "repeated_errors"
            suggestions.append(
                f"Same error occurring {max(errors_repeated.values())}x: "
                f'"{repeated_errors[0][:80]}"'
            )
            suggestions.append("Stop and debug the root cause before continuing.")

        # Check for failed iterations streak
        failed_count = sum(1 for i in iterations if not i.success)
        if failed_count >= self.MIN_ITERATIONS_FOR_DETECTION:
            fail_ratio = failed_count / len(iterations)
            if fail_ratio > 0.5:
                score += 20.0
                loop_type = "high_failure_rate"
                suggestions.append(
                    f"{failed_count}/{len(iterations)} iterations failed ({fail_ratio:.0%}). "
                    "Consider pausing to debug the underlying issue."
                )

        # Check for very short iterations (rapid-fire, possibly automated retry loops)
        durations = [i.duration_seconds for i in iterations if i.duration_seconds is not None]
        if durations:
            avg_duration = sum(durations) / len(durations)
            if avg_duration < 5.0 and len(iterations) >= 5:
                score += 10.0
                if loop_type == "none":
                    loop_type = "rapid_iterations"
                suggestions.append(
                    f"Average iteration duration is {avg_duration:.1f}s. "
                    "Rapid iterations may indicate automated retry loops."
                )

        # Cap score at 100
        score = min(100.0, score)

        # Determine severity
        if score >= self.CRITICAL_SCORE_THRESHOLD:
            severity = LoopSeverity.CRITICAL
        elif score >= self.HIGH_SCORE_THRESHOLD:
            severity = LoopSeverity.HIGH
        elif score > 0:
            severity = LoopSeverity.MEDIUM
        else:
            severity = LoopSeverity.LOW

        is_loop = score >= self.LOOP_THRESHOLD

        if not suggestions:
            suggestions.append("No loops detected. Your iterations look productive!")

        return LoopDetection(
            is_loop=is_loop,
            severity=severity,
            score=round(score, 1),
            loop_type=loop_type,
            repeated_files=repeated_files,
            repeated_errors=repeated_errors,
            iteration_count=len(iterations),
            suggestions=suggestions,
        )
