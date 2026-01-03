"""E2E test fixtures for Claude Code plugin testing."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def e2e_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create an isolated project directory for E2E testing.

    Sets up:
    - .claude/ directory for settings
    - Basic pyproject.toml for uv/ruff/black
    - Git repository (required for git validation tests)
    """
    # Create .claude directory
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Create pyproject.toml with standard ruff/black config
    # Mirrors the rules enforced by the plugin in strict mode
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[project]
name = "e2e-test-project"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade (type import modernization)
    "SLF",  # flake8-self (private member access)
    "TCH",  # flake8-type-checking
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["SLF001"]
"src/*/_internal/*.py" = ["SLF001"]

[tool.black]
line-length = 88
target-version = ["py312"]
"""
    )

    # Initialize git repo (needed for validate_git tests)
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    yield tmp_path


@pytest.fixture
def strict_settings(e2e_project: Path) -> Path:
    """Configure project for strict mode."""
    settings_path = e2e_project / ".claude" / "settings.json"
    settings_path.write_text(
        json.dumps({"plugins": {"python-dev-framework": {"level": "strict"}}}, indent=2)
    )
    return e2e_project


@pytest.fixture
def moderate_settings(e2e_project: Path) -> Path:
    """Configure project for moderate mode."""
    settings_path = e2e_project / ".claude" / "settings.json"
    settings_path.write_text(
        json.dumps(
            {"plugins": {"python-dev-framework": {"level": "moderate"}}}, indent=2
        )
    )
    return e2e_project


@pytest.fixture
def minimal_settings(e2e_project: Path) -> Path:
    """Configure project for minimal mode."""
    settings_path = e2e_project / ".claude" / "settings.json"
    settings_path.write_text(
        json.dumps(
            {"plugins": {"python-dev-framework": {"level": "minimal"}}}, indent=2
        )
    )
    return e2e_project
