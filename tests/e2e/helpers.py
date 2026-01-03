"""Helper utilities for E2E testing with Claude CLI."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Plugin source directory (python-dev-framework at project root)
PLUGIN_ROOT = Path(__file__).parent.parent.parent.absolute() / "python-dev-framework"


@dataclass
class ClaudeResult:
    """Result from Claude CLI invocation."""

    returncode: int
    stdout: str
    stderr: str
    output_json: dict[str, Any] | None = None

    @property
    def succeeded(self) -> bool:
        """Check if command succeeded."""
        return self.returncode == 0

    @property
    def was_blocked(self) -> bool:
        """Check if a PreToolUse hook blocked the operation."""
        # Check stderr for block indicators
        stderr_lower = self.stderr.lower()
        if "blocked" in stderr_lower or "denied" in stderr_lower:
            return True

        # Check JSON output for block indicators
        if self.output_json:
            # Check result text for "blocked" or "block"
            result = self.output_json.get("result", "")
            if isinstance(result, str) and "blocked" in result.lower():
                return True
            # Check for structured decision field
            if isinstance(result, dict) and result.get("decision") == "block":
                return True

        return False


def run_claude(
    prompt: str,
    *,
    project_dir: Path,
    plugin_dir: Path | None = None,
    timeout: int = 120,
    output_format: str = "json",
    allowed_tools: list[str] | None = None,
) -> ClaudeResult:
    """Execute Claude CLI with the plugin loaded.

    Args:
        prompt: The prompt to send to Claude
        project_dir: Working directory (simulated consumer project)
        plugin_dir: Plugin source directory to load (defaults to PLUGIN_ROOT)
        timeout: Command timeout in seconds
        output_format: "text", "json", or "stream-json"
        allowed_tools: Restrict to specific tools (e.g., ["Write", "Bash"])

    Returns:
        ClaudeResult with stdout, stderr, and parsed JSON if applicable
    """
    if plugin_dir is None:
        plugin_dir = PLUGIN_ROOT

    cmd = [
        "claude",
        "-p",  # Print mode (non-interactive)
        prompt,  # Prompt must follow -p immediately
        "--output-format",
        output_format,
        "--plugin-dir",
        str(plugin_dir),
        "--dangerously-skip-permissions",
    ]

    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

    env = os.environ.copy()

    try:
        result = subprocess.run(
            cmd,
            check=False,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        return ClaudeResult(
            returncode=-1,
            stdout=e.stdout or "" if isinstance(e.stdout, str) else "",
            stderr=f"Command timed out after {timeout}s",
        )

    output_json = None
    if output_format == "json" and result.stdout.strip():
        with contextlib.suppress(json.JSONDecodeError):
            output_json = json.loads(result.stdout)

    return ClaudeResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        output_json=output_json,
    )


def write_file_via_claude(
    project_dir: Path,
    file_path: str,
    content: str,
    *,
    plugin_dir: Path | None = None,
) -> ClaudeResult:
    """Use Claude to write a file (triggers PostToolUse hook).

    Args:
        project_dir: Working directory
        file_path: Relative path for the file to create
        content: Content to write
        plugin_dir: Plugin source directory

    Returns:
        ClaudeResult from the operation
    """
    # Escape content for prompt
    escaped_content = content.replace("```", "\\`\\`\\`")

    prompt = f"""Write exactly the following content to the file "{file_path}":

```
{escaped_content}
```

Use the Write tool. Create parent directories if needed. Do not modify the content."""

    return run_claude(
        prompt,
        project_dir=project_dir,
        plugin_dir=plugin_dir,
        allowed_tools=["Write"],
    )


def run_git_via_claude(
    project_dir: Path,
    git_command: str,
    *,
    plugin_dir: Path | None = None,
) -> ClaudeResult:
    """Use Claude to run a git command (triggers PreToolUse hook).

    Args:
        project_dir: Working directory (must be a git repo)
        git_command: The git command to run (e.g., "git checkout -b feature/foo")
        plugin_dir: Plugin source directory

    Returns:
        ClaudeResult from the operation
    """
    prompt = f"""Run this exact command: {git_command}

Use the Bash tool. Do not explain or add anything else."""

    return run_claude(
        prompt,
        project_dir=project_dir,
        plugin_dir=plugin_dir,
        allowed_tools=["Bash"],
    )
