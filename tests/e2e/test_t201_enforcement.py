"""E2E tests for T201 (print ban) enforcement.

Tests that TDD-002 implementation correctly enforces structlog usage over print()
in src/ directories through Ruff T201 rule.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .helpers import write_file_via_claude


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
]


class TestT201EnforcementE2E:
    """E2E tests for T201 print() ban in strict mode."""

    def test_print_in_src_file_created_with_warning(
        self,
        strict_settings: Path,
    ) -> None:
        """T201: print() in src/ should be written but flagged by ruff.

        In strict mode, ruff runs with all rules including T201. The file is
        still created (PostToolUse can't block), but ruff warnings are logged
        for Claude to potentially act on.
        """
        project_dir = strict_settings

        # Code with print statement (T201 violation)
        code_with_print = '''\
def greet(name: str) -> None:
    """Greet the user."""
    print(f"Hello, {name}")
'''

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/greeting.py",
            content=code_with_print,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        # File should be created (PostToolUse doesn't block)
        written_file = project_dir / "src" / "greeting.py"
        assert written_file.exists(), "File was not created"

        # File content should be formatted
        content = written_file.read_text()
        assert "def greet(name: str)" in content

    def test_structlog_usage_no_t201_warning(
        self,
        strict_settings: Path,
    ) -> None:
        """Code using structlog instead of print() should pass T201 cleanly."""
        project_dir = strict_settings

        # Code using structlog (proper pattern per TDD-002)
        code_with_structlog = '''\
import structlog

log = structlog.get_logger()


def greet(name: str) -> None:
    """Greet the user with structured logging."""
    log.info("user_greeted", name=name)
'''

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/greeting.py",
            content=code_with_structlog,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        written_file = project_dir / "src" / "greeting.py"
        assert written_file.exists()

        content = written_file.read_text()
        assert "structlog" in content
        assert "log.info" in content

    def test_print_in_tests_directory_allowed(
        self,
        strict_settings: Path,
    ) -> None:
        """T201: print() should be allowed in tests/ per per-file-ignores."""
        project_dir = strict_settings

        # Test file with print statements (allowed per pyproject.toml)
        test_code = '''\
def test_something() -> None:
    """Test with print for debugging."""
    print("Debug output")
    assert True
'''

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="tests/test_example.py",
            content=test_code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        written_file = project_dir / "tests" / "test_example.py"
        assert written_file.exists()

        content = written_file.read_text()
        # print should remain (not removed by ruff in tests/)
        assert "print" in content


class TestT201StrictnessLevelsE2E:
    """E2E tests verifying T201 behavior across strictness levels."""

    def test_moderate_mode_allows_print(
        self,
        moderate_settings: Path,
    ) -> None:
        """Moderate mode uses core rules only (E,W,F,I,B) - no T201 enforcement."""
        project_dir = moderate_settings

        code_with_print = '''\
def greet(name: str) -> None:
    """Greet with print (allowed in moderate mode)."""
    print(f"Hello, {name}")
'''

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/greeting.py",
            content=code_with_print,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        written_file = project_dir / "src" / "greeting.py"
        assert written_file.exists()

        content = written_file.read_text()
        # print should remain (not flagged in moderate mode)
        assert "print" in content

    def test_minimal_mode_allows_print(
        self,
        minimal_settings: Path,
    ) -> None:
        """Minimal mode only runs black - no ruff, no T201 enforcement."""
        project_dir = minimal_settings

        code_with_print = '''\
def greet(name: str) -> None:
    """Greet with print (allowed in minimal mode)."""
    print(f"Hello, {name}")
'''

        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/greeting.py",
            content=code_with_print,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        written_file = project_dir / "src" / "greeting.py"
        assert written_file.exists()

        content = written_file.read_text()
        # print should remain (ruff not run in minimal mode)
        assert "print" in content
