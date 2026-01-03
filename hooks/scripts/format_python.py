#!/usr/bin/env python3
"""Auto-format and type-check Python files after Edit/Write operations.

PostToolUse hook that runs ruff, black, and mypy on .py/.pyi files.
Behavior varies by strictness level per ADR-002.

Note: PostToolUse hooks react to completed operations. They cannot
block execution (tool already ran) but can perform post-processing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


# Ensure script directory is in path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))

from config import PluginConfig, load_config


def check_dependencies() -> str | None:
    """Verify required tools are available.

    Returns error message if dependency missing, None if all present.
    """
    if not shutil.which("uv"):
        return "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"

    result = subprocess.run(
        ["uv", "run", "ruff", "--version"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return "ruff not found in project. Run: uv add --dev ruff"

    result = subprocess.run(
        ["uv", "run", "black", "--version"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return "black not found in project. Run: uv add --dev black"

    return None


def check_future_annotations(file_path: Path) -> tuple[bool, str | None]:
    """Check for required 'from __future__ import annotations'.

    Args:
        file_path: Path to Python file

    Returns:
        (True, None) if present or file is empty/comments-only
        (False, error_message) if missing
    """
    content = file_path.read_text()

    # Skip if file is empty or only comments
    lines = [
        line
        for line in content.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        return True, None

    # Check for __future__ import
    if "from __future__ import annotations" not in content:
        return False, "Missing 'from __future__ import annotations' at top of file"

    return True, None


def get_version_specific_ignores(target_python: str) -> list[str]:
    """Get Ruff rules to ignore based on Python version.

    Args:
        target_python: Version string like "py39"

    Returns:
        List of rules to ignore, e.g., ["UP036"] for py39
    """
    ignores: list[str] = []

    if target_python == "py39":
        # Python 3.9 doesn't have match statements
        ignores.append("UP036")

    return ignores


def get_ruff_rules(target_python: str) -> list[str]:
    """Get additional Ruff rules based on Python version.

    Args:
        target_python: Version string like "py39"

    Returns:
        List of rules to add, e.g., ["FA"] for py39/py310
    """
    if target_python in ("py39", "py310"):
        return ["FA"]  # flake8-future-annotations
    return []


def convert_py_version(target_python: str) -> str:
    """Convert py39 to 3.9 for mypy --python-version.

    Args:
        target_python: Version string like "py39", "py312"

    Returns:
        Version string like "3.9", "3.12"
    """
    # py39 -> 3.9, py312 -> 3.12
    return target_python.replace("py3", "3.")


def output_block(reason: str) -> None:
    """Output JSON block response for hook protocol."""
    print(json.dumps({"decision": "block", "reason": reason}))


def check_lint_errors(
    file_path: str,
    config: PluginConfig,
    rule_select: str | None = None,
) -> list[str]:
    """Check for remaining lint errors after auto-fix.

    Runs ruff check (without --fix) to find unfixable errors like SLF001.

    Args:
        file_path: Path to Python file
        config: Plugin configuration
        rule_select: Optional rule selection string (e.g., "E,W,F,I,B,UP").
                     If None, uses full rule set from pyproject.toml.

    Returns:
        List of lint error messages (empty if none)
    """
    ruff_cmd = [
        "uv",
        "run",
        "ruff",
        "check",
        "--target-version",
        config.target_python,
        file_path,
    ]

    # Add rule selection if specified (for moderate mode)
    if rule_select:
        ruff_cmd.insert(-1, f"--select={rule_select}")

    # Add version-specific ignores
    for ignore in get_version_specific_ignores(config.target_python):
        ruff_cmd.insert(-1, "--ignore")
        ruff_cmd.insert(-1, ignore)

    # Add version-specific rules (FA for py39/py310)
    for rule in get_ruff_rules(config.target_python):
        ruff_cmd.insert(-1, "--extend-select")
        ruff_cmd.insert(-1, rule)

    result = subprocess.run(
        ruff_cmd,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 and result.stdout.strip():
        # Parse ruff output - filter to just error lines
        errors = [
            line.strip()
            for line in result.stdout.strip().split("\n")
            if line.strip() and not line.startswith("Found")
        ]
        return errors

    return []


def format_file(file_path: str, config: PluginConfig) -> list[str]:
    """Run formatters on file based on strictness level.

    Returns list of unfixable lint errors (empty if none).
    """
    if config.level == "minimal":
        # Black only
        subprocess.run(
            ["uv", "run", "black", file_path],
            check=False,
            capture_output=True,
        )
        return []
    elif config.level == "moderate":
        # Core ruff rules + UP (type imports) + black (with target version)
        # TDD-004: UP rules auto-fix deprecated type imports
        moderate_rules = "E,W,F,I,B,UP"
        ruff_cmd = [
            "uv",
            "run",
            "ruff",
            "check",
            "--fix",
            "--target-version",
            config.target_python,
            f"--select={moderate_rules}",
            file_path,
        ]
        subprocess.run(ruff_cmd, check=False, capture_output=True)
        subprocess.run(
            ["uv", "run", "black", file_path],
            check=False,
            capture_output=True,
        )

        # Pass 2: Check for remaining unfixable errors and warn (per TDD-004/006)
        unfixed_errors = check_lint_errors(
            file_path, config, rule_select=moderate_rules
        )
        if unfixed_errors:
            for error in unfixed_errors:
                print(f"Warning: {error}", file=sys.stderr)

        return []  # Moderate mode warns only, doesn't block
    else:  # strict
        # Full ruff + black (with target version and version-specific rules)
        ruff_cmd = [
            "uv",
            "run",
            "ruff",
            "check",
            "--fix",
            "--target-version",
            config.target_python,
            file_path,
        ]

        # Add version-specific ignores
        for ignore in get_version_specific_ignores(config.target_python):
            ruff_cmd.insert(-1, "--ignore")
            ruff_cmd.insert(-1, ignore)

        # Add version-specific rules (FA for py39/py310)
        for rule in get_ruff_rules(config.target_python):
            ruff_cmd.insert(-1, "--extend-select")
            ruff_cmd.insert(-1, rule)

        subprocess.run(ruff_cmd, check=False, capture_output=True)
        subprocess.run(
            ["uv", "run", "black", file_path],
            check=False,
            capture_output=True,
        )

        # Check for remaining unfixable errors (e.g., SLF001)
        return check_lint_errors(file_path, config)


def check_types(file_path: str, config: PluginConfig) -> list[str]:
    """Run mypy type checking based on strictness level.

    Per ADR-002:
    - strict: Warn on type errors
    - moderate: Skip type checking
    - minimal: Skip type checking

    Returns list of type error messages (empty if none or skipped).
    """
    if config.level != "strict":
        return []

    # Check if mypy is available
    version_check = subprocess.run(
        ["uv", "run", "mypy", "--version"],
        check=False,
        capture_output=True,
    )
    if version_check.returncode != 0:
        return ["mypy not found in project. Run: uv add --dev mypy"]

    # Convert target version for mypy (py39 -> 3.9)
    python_version = convert_py_version(config.target_python)

    # Run mypy on the file with version-aware settings
    mypy_result = subprocess.run(
        [
            "uv",
            "run",
            "mypy",
            "--strict",
            "--python-version",
            python_version,
            file_path,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if mypy_result.returncode != 0 and mypy_result.stdout.strip():
        # Parse mypy output - each line is an error
        errors = [
            line.strip()
            for line in mypy_result.stdout.strip().split("\n")
            if line.strip() and not line.startswith("Found")
        ]
        return errors

    return []


def read_stdin_context() -> dict[str, Any]:
    """Read hook context from stdin."""
    try:
        return json.loads(sys.stdin.read())  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {}


def main() -> None:
    """Hook entry point."""
    context = read_stdin_context()

    tool_name = context.get("tool_name", "")
    tool_input = context.get("tool_input", {})

    # Verify tool type (defense in depth beyond hooks.json matcher)
    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    # Skip non-Python files
    if not file_path.endswith((".py", ".pyi")):
        sys.exit(0)

    # Skip if file doesn't exist (e.g., deleted)
    if not Path(file_path).exists():
        sys.exit(0)

    # Check dependencies - block if missing (strict mode enforcement)
    if error := check_dependencies():
        output_block(f"Missing dependency: {error}")
        return

    # Get project root for version detection
    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    config = load_config(project_root)

    # Check __future__ annotations (strict mode only, per TDD-003)
    if config.level == "strict":
        ok, error = check_future_annotations(Path(file_path))
        if not ok and error:
            output_block(error)
            return

    lint_errors = format_file(file_path, config)

    # Type checking (strict mode only, per ADR-002)
    type_errors = check_types(file_path, config)

    # Build response using Claude Code's expected format
    all_errors: list[str] = []
    if lint_errors:
        all_errors.append(f"Lint errors in {file_path}:\n" + "\n".join(lint_errors))
    if type_errors:
        all_errors.append(f"Type errors in {file_path}:\n" + "\n".join(type_errors))

    if all_errors:
        output_block("\n\n".join(all_errors))
    # No output needed for success - Claude Code doesn't require it


if __name__ == "__main__":
    main()
