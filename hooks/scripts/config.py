"""Shared configuration loader for plugin hooks."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# Python 3.9-3.10 compatibility for tomllib
if sys.version_info >= (3, 11):  # noqa: UP036
    import tomllib
else:
    import tomli as tomllib


StrictnessLevel = Literal["strict", "moderate", "minimal"]

DEFAULT_BRANCH_TYPES = [
    "feature",
    "bugfix",
    "hotfix",
    "refactor",
    "docs",
    "test",
    "chore",
]
DEFAULT_COMMIT_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
]


@dataclass
class PluginConfig:
    """Plugin configuration with defaults."""

    level: StrictnessLevel = "strict"
    target_python: str = "py312"
    branch_types: list[str] = field(default_factory=lambda: DEFAULT_BRANCH_TYPES.copy())
    commit_types: list[str] = field(default_factory=lambda: DEFAULT_COMMIT_TYPES.copy())


def detect_python_version(project_root: Path) -> str:
    """Detect target Python version from pyproject.toml.

    Priority:
    1. tool.ruff.target-version (e.g., "py39")
    2. project.requires-python (e.g., ">=3.9" -> "py39")
    3. Default to "py312"

    Args:
        project_root: Path to project root containing pyproject.toml

    Returns:
        Python version string like "py39", "py310", "py312"
    """
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return "py312"

    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)

        # Priority 1: Ruff target-version
        ruff_target = data.get("tool", {}).get("ruff", {}).get("target-version")
        if ruff_target:
            return str(ruff_target)

        # Priority 2: project.requires-python
        requires = data.get("project", {}).get("requires-python", "")
        # Match >=, >, or ~= version specifiers
        match = re.search(r"(?:>=?|~=)\s*3\.(\d+)", requires)
        if match:
            minor = match.group(1)
            return f"py3{minor}"

    except (tomllib.TOMLDecodeError, OSError):
        pass

    return "py312"


def load_config(project_root: Path | None = None) -> PluginConfig:
    """Load plugin configuration from consumer project settings.

    Reads from $CLAUDE_PROJECT_DIR/.claude/settings.json.
    Returns defaults if file missing or invalid.

    Args:
        project_root: Optional project root for Python version detection.
                      If None, uses CLAUDE_PROJECT_DIR env var.
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    settings_path = Path(project_dir) / ".claude" / "settings.json"

    # Determine project root for version detection
    if project_root is None:
        project_root = Path(project_dir)

    target_python = detect_python_version(project_root)

    if not settings_path.exists():
        return PluginConfig(target_python=target_python)

    try:
        data = json.loads(settings_path.read_text())
        plugin_config = data.get("plugins", {}).get("python-dev-framework", {})

        level = plugin_config.get("level", "strict")
        if level not in ("strict", "moderate", "minimal"):
            level = "strict"

        return PluginConfig(
            level=level,
            target_python=target_python,
            branch_types=plugin_config.get("branch_types", DEFAULT_BRANCH_TYPES.copy()),
            commit_types=plugin_config.get("commit_types", DEFAULT_COMMIT_TYPES.copy()),
        )
    except (json.JSONDecodeError, TypeError, KeyError):
        return PluginConfig(target_python=target_python)
