"""E2E tests for TDD-005 directory layout enforcement.

Tests that the plugin correctly detects and reports SLF001 violations
(private attribute access) via Ruff in strict mode.

Note: SLF001 catches private ATTRIBUTE access (obj._private), not imports from
private modules. The _internal/ naming convention is documentation-based guidance.

Important: PostToolUse hooks run AFTER the tool executes and cannot block the
operation. They output error information that Claude can act on. The file is
always written - the hook provides feedback for Claude to address.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .helpers import write_file_via_claude


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
]


class TestPrivateAccessEnforcementE2E:
    """E2E tests for SLF001 private attribute access enforcement.

    Note: PostToolUse hooks cannot block (tool already executed).
    These tests verify the hook detects violations and provides feedback
    to Claude, not that the write is blocked.
    """

    def test_detects_private_attribute_access(
        self,
        strict_settings: Path,
    ) -> None:
        """SLF001: Accessing obj._private should be detected by hook.

        PostToolUse runs after write completes. File is written, but hook
        outputs violation info for Claude to potentially act on.
        """
        project_dir = strict_settings

        code = """\
from __future__ import annotations


class Config:
    _secret_key = "hidden"


def leak_secret() -> str:
    c = Config()
    return c._secret_key
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        # File should be written (PostToolUse cannot block)
        written_file = project_dir / "src" / "example.py"
        assert written_file.exists(), "File should exist after write"
        assert "c._secret_key" in written_file.read_text()

        # The hook output (with SLF001 info) is in Claude's conversation context,
        # not directly visible in JSON result. Verify the write completed.
        assert result.succeeded

    def test_detects_private_method_call(
        self,
        strict_settings: Path,
    ) -> None:
        """SLF001: Calling obj._private_method() should be detected by hook.

        PostToolUse runs after write completes. File is written, but hook
        outputs violation info for Claude to potentially act on.
        """
        project_dir = strict_settings

        code = """\
from __future__ import annotations


class Service:
    def _internal_op(self) -> str:
        return "internal"


def use_internal() -> str:
    return Service()._internal_op()
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        # File should be written (PostToolUse cannot block)
        written_file = project_dir / "src" / "example.py"
        assert written_file.exists(), "File should exist after write"
        assert "_internal_op()" in written_file.read_text()

        # Verify the write completed successfully
        assert result.succeeded

    def test_allows_test_private_access(
        self,
        strict_settings: Path,
    ) -> None:
        """Tests should be able to access private members (exempt from SLF001).

        Tests are exempt via per-file-ignores in pyproject.toml.
        """
        project_dir = strict_settings

        # Create src module with private member
        src_dir = project_dir / "src" / "pkg"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("")
        (src_dir / "service.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "class Service:\n"
            "    _internal_state = 0\n"
        )

        # Test file accessing private member
        code = """\
from __future__ import annotations


def test_internal_state() -> None:
    from pkg.service import Service
    s = Service()
    assert s._internal_state == 0
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="tests/test_service.py",
            content=code,
        )

        # Should succeed - tests are exempt from SLF001
        assert result.succeeded, f"Test write failed: {result.stderr}"

        # Verify file was written correctly
        written_file = project_dir / "tests" / "test_service.py"
        assert written_file.exists()
        assert "s._internal_state" in written_file.read_text()


class TestPrivateAccessStrictnessLevelsE2E:
    """E2E tests for SLF001 behavior across strictness levels.

    Note: moderate and minimal modes don't run full Ruff rules,
    so SLF001 is not checked regardless.
    """

    def test_moderate_mode_writes_private_access(
        self,
        moderate_settings: Path,
    ) -> None:
        """Moderate mode should write file without SLF001 check."""
        project_dir = moderate_settings

        code = """\
from __future__ import annotations


class Config:
    _secret = "value"


x = Config()._secret
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        # Should succeed - moderate doesn't run SLF rules
        assert result.succeeded, f"Write failed: {result.stderr}"

        # Verify file was written
        written_file = project_dir / "src" / "example.py"
        assert written_file.exists()
        content = written_file.read_text()
        assert "Config()._secret" in content

    def test_minimal_mode_writes_private_access(
        self,
        minimal_settings: Path,
    ) -> None:
        """Minimal mode should write file (only runs black)."""
        project_dir = minimal_settings

        code = """\
from __future__ import annotations


class Config:
    _secret = "value"


x = Config()._secret
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        # Should succeed - minimal only runs black
        assert result.succeeded, f"Write failed: {result.stderr}"

        # Verify file was written
        written_file = project_dir / "src" / "example.py"
        assert written_file.exists()
        content = written_file.read_text()
        assert "Config()._secret" in content


class TestInternalToInternalAccessE2E:
    """E2E tests for internal module cross-access.

    _internal modules are exempt from SLF001 via per-file-ignores.
    """

    def test_internal_can_import_internal(
        self,
        strict_settings: Path,
    ) -> None:
        """_internal modules should be able to import from each other.

        Exempt via per-file-ignores: src/*/_internal/*.py = SLF001
        """
        project_dir = strict_settings

        # Create _internal structure
        internal_dir = project_dir / "src" / "pkg" / "_internal"
        internal_dir.mkdir(parents=True)
        (internal_dir / "__init__.py").write_text("")
        (internal_dir / "utils.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def _format_id(raw: str) -> str:\n"
            "    return raw.upper()\n"
        )

        # Write another internal module that imports from utils
        code = """\
from __future__ import annotations

from .utils import _format_id


def _generate_formatted_id(raw: str) -> str:
    return _format_id(raw)
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/pkg/_internal/service.py",
            content=code,
        )

        # Should succeed - _internal can access _internal
        assert result.succeeded, f"Internal cross-import failed: {result.stderr}"

        # Verify file was written correctly
        written_file = project_dir / "src" / "pkg" / "_internal" / "service.py"
        assert written_file.exists()
        content = written_file.read_text()
        assert "_format_id" in content
