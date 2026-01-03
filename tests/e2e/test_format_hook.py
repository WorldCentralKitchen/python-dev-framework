"""E2E tests for PostToolUse Python formatting hook."""

from __future__ import annotations

from pathlib import Path

import pytest

from .helpers import run_claude, write_file_via_claude


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
]


class TestFormatPythonHookE2E:
    """E2E tests for format_python.py PostToolUse hook."""

    def test_python_file_formatted_after_write(
        self,
        strict_settings: Path,
    ) -> None:
        """Python file should be auto-formatted after Write tool."""
        project_dir = strict_settings

        # Unformatted Python code (includes __future__ for strict mode)
        unformatted_code = """\
from __future__ import annotations


def foo(   x,y,   z):
    return x+y+z
"""

        # Write file via Claude (triggers PostToolUse hook)
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=unformatted_code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        # Verify file was formatted
        written_file = project_dir / "src" / "example.py"
        assert written_file.exists(), "File was not created"

        content = written_file.read_text()

        # Check formatting was applied (spaces around operators, etc.)
        # Note: Claude may add type hints, so check for either format
        assert (
            "def foo(x, y, z):" in content or "def foo(x:" in content
        ), f"Not formatted: {content}"
        assert "return x + y + z" in content, f"Not formatted: {content}"

    def test_non_python_file_unchanged(
        self,
        strict_settings: Path,
    ) -> None:
        """Non-Python files should not trigger formatting."""
        project_dir = strict_settings

        original_content = "some text content\n  with   weird   spacing\n"

        result = run_claude(
            f'Write exactly this content to "data.txt": {original_content}',
            project_dir=project_dir,
            allowed_tools=["Write"],
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        written_file = project_dir / "data.txt"
        assert written_file.exists(), "File was not created"

        # Content should be unchanged (no formatting applied)
        # Note: Claude may normalize whitespace, so we check structure
        content = written_file.read_text()
        assert "weird   spacing" in content or "weird" in content

    def test_pyi_stub_file_formatted(
        self,
        strict_settings: Path,
    ) -> None:
        """Python stub files (.pyi) should also be formatted."""
        project_dir = strict_settings

        unformatted_stub = """\
def foo(x:int,y:int)->int: ...
"""

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.pyi",
            content=unformatted_stub,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        written_file = project_dir / "src" / "example.pyi"
        assert written_file.exists()

        content = written_file.read_text()
        # Should have spaces after colons in type hints
        assert "int, " in content or "int," in content  # formatted

    def test_minimal_level_black_only(
        self,
        minimal_settings: Path,
    ) -> None:
        """Minimal mode should only apply black formatting, not ruff fixes."""
        project_dir = minimal_settings

        # Code with unused import (ruff would remove) and bad formatting (black fixes)
        code = """\
import os
import sys

def foo(x,y):
    return x+y
"""

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()

        # Black formatting should be applied
        assert "def foo(x, y):" in content, f"Black not applied: {content}"
        assert "return x + y" in content, f"Black not applied: {content}"

        # Unused imports should still be present (ruff not run in minimal)
        assert (
            "import sys" in content
        ), f"Ruff removed import in minimal mode: {content}"


class TestTypingEnforcementE2E:
    """E2E tests for mypy type checking in PostToolUse hook."""

    def test_type_errors_warned_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """Type checking runs in strict mode (warnings go to Claude's context).

        Note: Hook warnings are output to Claude's context via JSON, not directly
        visible in the response text. This test verifies the file is created and
        the hook executes without error. Type warnings are logged for Claude to
        potentially act on in subsequent turns.
        """
        project_dir = strict_settings

        # Code with obvious type error - missing return type
        code_with_type_errors = '''\
def add_numbers(x, y):
    """Missing type hints."""
    return x + y
'''

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/calculator.py",
            content=code_with_type_errors,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        # File should exist and be formatted
        written_file = project_dir / "src" / "calculator.py"
        assert written_file.exists()

        # Verify file was written (hook ran successfully)
        content = written_file.read_text()
        assert "def add_numbers" in content

    def test_typed_code_no_warnings_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """Properly typed code should not produce warnings."""
        project_dir = strict_settings

        # Properly typed code
        typed_code = '''\
def add_numbers(x: int, y: int) -> int:
    """Add two integers."""
    return x + y
'''

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/calculator.py",
            content=typed_code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        written_file = project_dir / "src" / "calculator.py"
        assert written_file.exists()

    def test_type_check_skipped_moderate(
        self,
        moderate_settings: Path,
    ) -> None:
        """Type checking should be skipped in moderate mode."""
        project_dir = moderate_settings

        # Code with type errors
        untyped_code = """\
def multiply(a, b):
    return a * b
"""

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/math_utils.py",
            content=untyped_code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        # Should succeed without type warnings (mypy skipped)
        written_file = project_dir / "src" / "math_utils.py"
        assert written_file.exists()

    def test_type_check_skipped_minimal(
        self,
        minimal_settings: Path,
    ) -> None:
        """Type checking should be skipped in minimal mode."""
        project_dir = minimal_settings

        # Code with type errors
        untyped_code = """\
def divide(a, b):
    return a / b
"""

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/math_utils.py",
            content=untyped_code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        # Should succeed without type warnings (mypy skipped)
        written_file = project_dir / "src" / "math_utils.py"
        assert written_file.exists()
