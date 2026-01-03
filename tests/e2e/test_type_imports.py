"""E2E tests for TDD-004 type import pattern enforcement.

Tests that the plugin correctly auto-fixes deprecated type imports via Ruff
UP rules (UP006, UP007, UP035).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .helpers import write_file_via_claude


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
]


class TestTypeImportAutoFixE2E:
    """E2E tests for type import auto-fix behavior."""

    def test_fixes_typing_list_to_builtin(
        self,
        strict_settings: Path,
    ) -> None:
        """UP006: typing.List should be fixed to list."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations

from typing import List


def get_names() -> List[str]:
    return []
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        assert "list[str]" in content
        assert "List[str]" not in content

    def test_fixes_union_to_pipe_syntax(
        self,
        strict_settings: Path,
    ) -> None:
        """UP007: Union[X, Y] should be fixed to X | Y."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations

from typing import Union


def process(value: Union[str, int]) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        assert "str | int" in content
        assert "Union" not in content

    def test_fixes_optional_to_pipe_none(
        self,
        strict_settings: Path,
    ) -> None:
        """UP007: Optional[X] should be fixed to X | None."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations

from typing import Optional


def get_name() -> Optional[str]:
    return None
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        assert "str | None" in content
        assert "Optional" not in content

    def test_fixes_typing_dict_to_builtin(
        self,
        strict_settings: Path,
    ) -> None:
        """UP006: typing.Dict should be fixed to dict."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations

from typing import Dict


def get_data() -> Dict[str, int]:
    return {}
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        assert "dict[str, int]" in content
        assert "Dict[str, int]" not in content


class TestTypeImportStrictnessLevelsE2E:
    """E2E tests for type import behavior across strictness levels."""

    def test_moderate_mode_fixes_type_imports(
        self,
        moderate_settings: Path,
    ) -> None:
        """Moderate mode should auto-fix UP rules."""
        project_dir = moderate_settings

        code = """\
from __future__ import annotations

from typing import List

x: List[int] = []
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        assert "list[int]" in content
        assert "List[int]" not in content

    def test_minimal_mode_preserves_old_syntax(
        self,
        minimal_settings: Path,
    ) -> None:
        """Minimal mode should NOT auto-fix type imports."""
        project_dir = minimal_settings

        code = """\
from __future__ import annotations

from typing import List

x: List[int] = []
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        # List should remain (ruff not run in minimal mode)
        assert "List[int]" in content
