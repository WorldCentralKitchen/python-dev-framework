"""Tests for TDD-006 immutability pattern enforcement.

Tests that Ruff catches mutable default patterns (B006, B039, RUF012)
and that mypy + useful-types catches SequenceNotStr violations.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


class TestRuffMutableDefaults:
    """Tests for Ruff mutable default detection."""

    def test_catches_mutable_argument_default(self, tmp_path: Path) -> None:
        """B006: Mutable argument default should be detected."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations


def process(items: list[str] = []) -> None:
    pass
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        assert "B006" in result.stdout

    def test_catches_mutable_dict_default(self, tmp_path: Path) -> None:
        """B006: Mutable dict default should be detected."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations


def process(config: dict[str, int] = {}) -> None:
    pass
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        assert "B006" in result.stdout

    def test_catches_mutable_set_default(self, tmp_path: Path) -> None:
        """B006: Mutable set default should be detected."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations


def process(items: set[str] = set()) -> None:
    pass
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        assert "B006" in result.stdout

    def test_catches_mutable_contextvar_default(self, tmp_path: Path) -> None:
        """B039: Mutable contextvar default should be detected."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations

from contextvars import ContextVar


items: ContextVar[list[str]] = ContextVar("items", default=[])
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        assert "B039" in result.stdout

    def test_catches_mutable_class_default(self, tmp_path: Path) -> None:
        """RUF008/RUF012: Mutable class default in dataclass should be detected."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    items: list[str] = []
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        # RUF008 or RUF012 catches mutable dataclass defaults
        assert "RUF008" in result.stdout or "RUF012" in result.stdout


class TestRuffAutoFix:
    """Tests for Ruff auto-fix behavior on mutable defaults."""

    def test_detects_mutable_argument_default(self, tmp_path: Path) -> None:
        """B006: Mutable argument default should be detected (not auto-fixed).

        B006's fix is classified as "unsafe" by ruff because it changes code
        behavior. We detect and block/warn rather than auto-fix.
        """
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations


def process(items: list[str] = []) -> None:
    pass
""")

        # Run ruff check (without --unsafe-fixes, B006 is detected but not fixed)
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False,
            capture_output=True,
            text=True,
        )

        # B006 should be detected
        assert "B006" in result.stdout
        assert result.returncode != 0

    def test_detects_mutable_class_default(self, tmp_path: Path) -> None:
        """RUF008: Mutable class default is detected (requires manual fix)."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    items: list[str] = []
""")

        # RUF008 is not auto-fixable - verify it's detected
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        # Should detect mutable default
        assert result.returncode != 0
        assert "RUF008" in result.stdout or "mutable" in result.stdout.lower()


class TestMypySequenceNotStr:
    """Tests for mypy SequenceNotStr enforcement via useful-types."""

    @pytest.mark.slow
    def test_catches_str_passed_to_sequence_not_str(self, tmp_path: Path) -> None:
        """mypy should catch str passed to SequenceNotStr[str] parameter."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations

from useful_types import SequenceNotStr


def process_tags(tags: SequenceNotStr[str]) -> None:
    for tag in tags:
        print(tag)


process_tags("hello")
""")

        result = subprocess.run(
            ["uv", "run", "mypy", "--strict", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        # mypy should report type error
        assert result.returncode != 0
        assert "SequenceNotStr" in result.stdout or "str" in result.stdout

    @pytest.mark.slow
    def test_allows_list_to_sequence_not_str(self, tmp_path: Path) -> None:
        """mypy should allow list[str] passed to SequenceNotStr[str]."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations

from useful_types import SequenceNotStr


def process_tags(tags: SequenceNotStr[str]) -> None:
    for tag in tags:
        print(tag)


process_tags(["hello", "world"])
""")

        result = subprocess.run(
            ["uv", "run", "mypy", "--strict", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        # mypy should pass (or only have unrelated errors)
        # We check that SequenceNotStr is not in the error output
        assert "SequenceNotStr" not in result.stdout


class TestCorrectPatterns:
    """Tests that correct immutability patterns are accepted."""

    def test_accepts_none_default_with_or_pattern(self, tmp_path: Path) -> None:
        """None default with 'or' pattern should be accepted."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations


def process(items: list[str] | None = None) -> None:
    items = items or []
    pass
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        assert "B006" not in result.stdout
        assert result.returncode == 0

    def test_accepts_field_default_factory(self, tmp_path: Path) -> None:
        """field(default_factory=list) should be accepted."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Config:
    items: list[str] = field(default_factory=list)
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        assert "RUF012" not in result.stdout

    def test_accepts_frozen_dataclass(self, tmp_path: Path) -> None:
        """Frozen dataclass should be accepted."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: float
    y: float
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_accepts_tuple_return(self, tmp_path: Path) -> None:
        """Tuple return type should be accepted."""
        file = tmp_path / "example.py"
        file.write_text("""\
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def get_names(paths: Iterable[Path]) -> tuple[str, ...]:
    return tuple(p.name for p in paths)
""")

        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(file)],
            check=False, capture_output=True,
            text=True,
        )

        # No B006/B039/RUF008/RUF012 errors (may have TCH warnings but those are OK)
        assert "B006" not in result.stdout
        assert "B039" not in result.stdout
        assert "RUF008" not in result.stdout
        assert "RUF012" not in result.stdout
