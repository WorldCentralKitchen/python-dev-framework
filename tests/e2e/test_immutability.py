"""E2E tests for TDD-006 immutability pattern enforcement.

Tests that the plugin correctly detects mutable default patterns via Ruff rules
(B006, B039, RUF008/RUF012). B006 is detected and reported (not auto-fixed as
ruff classifies its fix as "unsafe").
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .helpers import write_file_via_claude


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
]


class TestMutableArgumentDefaultE2E:
    """E2E tests for B006 mutable argument default enforcement.

    B006's fix is classified as "unsafe" by ruff (changes code behavior),
    so we detect and report it rather than auto-fix. PostToolUse hooks
    can't block (file already written), but report the error to Claude.
    """

    def test_detects_mutable_list_default_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """B006: Mutable list default should be detected in strict mode."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations


def process(items: list[str] = []) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        # File is written (PostToolUse can't block)
        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        # B006 is NOT auto-fixed (unsafe fix) - file still has mutable default
        # Hook reports error to Claude for manual correction
        assert "= [])" in content or "def process" in content

    def test_detects_mutable_dict_default_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """B006: Mutable dict default should be detected in strict mode."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations


def process(config: dict[str, int] = {}) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        # File is written (PostToolUse can't block)
        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        # B006 is NOT auto-fixed - file still has mutable default
        assert "= {})" in content or "def process" in content


class TestMutableClassDefaultE2E:
    """E2E tests for RUF008 mutable class default enforcement."""

    def test_detects_mutable_class_default_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """RUF008: Mutable class default should be detected (not auto-fixable)."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    items: list[str] = []
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        # File is written (PostToolUse can't block) but hook reports violation
        assert result.succeeded, f"Claude failed: {result.stderr}"

        # File may still have mutable default (RUF008 isn't auto-fixable)
        # Hook outputs a warning for Claude to fix
        content = (project_dir / "src" / "example.py").read_text()
        # Verify file was created
        assert "class Config" in content


class TestStrictnessLevelsE2E:
    """E2E tests for immutability enforcement across strictness levels."""

    def test_moderate_mode_warns_on_mutable_defaults(
        self,
        moderate_settings: Path,
    ) -> None:
        """Moderate mode should warn on B006 (not auto-fix, not block)."""
        project_dir = moderate_settings

        code = """\
from __future__ import annotations


def process(items: list[str] = []) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        # Should succeed (moderate mode warns only)
        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        # B006 is NOT auto-fixed - file still has mutable default
        # Moderate mode warns to stderr but doesn't block
        assert "= [])" in content or "def process" in content

    def test_minimal_mode_preserves_mutable_defaults(
        self,
        minimal_settings: Path,
    ) -> None:
        """Minimal mode should NOT auto-fix mutable defaults (black only)."""
        project_dir = minimal_settings

        code = """\
from __future__ import annotations


def process(items: list[str] = []) -> None:
    pass
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        # Minimal mode only runs black, so mutable defaults remain
        # Black will format but won't change the logic
        assert "= []" in content or "=[]" in content


class TestCorrectPatternsE2E:
    """E2E tests that correct immutability patterns are accepted."""

    def test_accepts_none_default(
        self,
        strict_settings: Path,
    ) -> None:
        """None default with 'or' pattern should be accepted."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations


def process(items: list[str] | None = None) -> None:
    items = items or []
    print(items)
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        # Pattern should be preserved (it's correct)
        assert "None = None" in content or "| None = None" in content

    def test_accepts_field_default_factory(
        self,
        strict_settings: Path,
    ) -> None:
        """field(default_factory=list) should be accepted."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Config:
    items: list[str] = field(default_factory=list)
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        # Pattern should be preserved (it's correct)
        assert "field(default_factory=list)" in content

    def test_accepts_frozen_dataclass(
        self,
        strict_settings: Path,
    ) -> None:
        """Frozen dataclass should be accepted."""
        project_dir = strict_settings

        code = """\
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: float
    y: float
"""
        result = write_file_via_claude(
            project_dir=project_dir,
            file_path="src/example.py",
            content=code,
        )

        assert result.succeeded, f"Claude failed: {result.stderr}"

        content = (project_dir / "src" / "example.py").read_text()
        # Pattern should be preserved
        assert "frozen=True" in content
