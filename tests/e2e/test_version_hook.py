"""E2E tests for Python version compatibility hook (TDD-003)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .helpers import write_file_via_claude


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
]


class TestFutureAnnotationsEnforcement:
    """E2E tests for __future__ annotations enforcement."""

    def test_flags_missing_future_annotations_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """Strict mode should flag missing __future__ import."""
        project_dir = strict_settings

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        code_without_future = """\
def foo(x: str | None) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code_without_future,
        )

        # PostToolUse hook should output block message
        # The tool still succeeds but outputs a block decision
        assert result.succeeded
        # Check stdout for block indicator
        if result.output_json:
            result_text = str(result.output_json.get("result", ""))
            assert "__future__" in result_text.lower() or "block" in result_text.lower()

    def test_allows_with_future_annotations_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """File with __future__ import should pass in strict mode."""
        project_dir = strict_settings

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        code_with_future = """\
from __future__ import annotations


def foo(x: str | None) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code_with_future,
        )

        assert result.succeeded
        # Verify file was written
        written = (project_dir / "src" / "example.py").read_text()
        assert "from __future__ import annotations" in written

    def test_moderate_mode_skips_future_check(
        self,
        moderate_settings: Path,
    ) -> None:
        """Moderate mode should not enforce __future__ annotations."""
        project_dir = moderate_settings

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        code_without_future = """\
def foo(x: str | None) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code_without_future,
        )

        # Should succeed without block message
        assert result.succeeded

    def test_minimal_mode_skips_future_check(
        self,
        minimal_settings: Path,
    ) -> None:
        """Minimal mode should not enforce __future__ annotations."""
        project_dir = minimal_settings

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        code_without_future = """\
def foo(x: str | None) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code_without_future,
        )

        # Should succeed without block message
        assert result.succeeded


class TestVersionDetection:
    """E2E tests for Python version detection from pyproject.toml."""

    def test_respects_ruff_target_version(
        self,
        e2e_project: Path,
    ) -> None:
        """Hook should use ruff target-version from pyproject.toml."""
        project_dir = e2e_project

        # Update pyproject.toml with py39 target
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text(
            """\
[project]
name = "test"
version = "0.1.0"
requires-python = ">=3.9"

[tool.ruff]
target-version = "py39"
line-length = 88

[tool.black]
line-length = 88
"""
        )

        # Set strict mode
        settings = project_dir / ".claude" / "settings.json"
        settings.write_text(
            json.dumps(
                {"plugins": {"python-dev-framework": {"level": "strict"}}},
                indent=2,
            )
        )

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        code = """\
from __future__ import annotations


def foo(x: str | None) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded

    def test_respects_requires_python(
        self,
        e2e_project: Path,
    ) -> None:
        """Hook should detect version from requires-python when no ruff target."""
        project_dir = e2e_project

        # Update pyproject.toml with only requires-python
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text(
            """\
[project]
name = "test"
version = "0.1.0"
requires-python = ">=3.10"

[tool.black]
line-length = 88
"""
        )

        # Set strict mode
        settings = project_dir / ".claude" / "settings.json"
        settings.write_text(
            json.dumps(
                {"plugins": {"python-dev-framework": {"level": "strict"}}},
                indent=2,
            )
        )

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        code = """\
from __future__ import annotations


def foo(x: str | None) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded
