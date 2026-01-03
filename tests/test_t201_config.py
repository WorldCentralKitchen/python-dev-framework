"""Tests for T201 (print ban) Ruff configuration.

Verifies that TDD-002 implementation correctly configures Ruff to ban print()
in src/ directories while exempting tests and hook scripts.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest


# Python 3.9-3.10 compatibility (project supports >=3.9)
if sys.version_info >= (3, 11):  # noqa: UP036
    import tomllib
else:
    import tomli as tomllib


@pytest.fixture(scope="module")
def ruff_config() -> dict[str, Any]:
    """Load Ruff configuration from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        config: dict[str, Any] = tomllib.load(f)
    lint_config: dict[str, Any] = config["tool"]["ruff"]["lint"]
    return lint_config


class TestT201RuffConfiguration:
    """Verify T201 print ban is correctly configured in Ruff."""

    def test_ruff_select_includes_flake8_print(
        self,
        ruff_config: dict[str, Any],
    ) -> None:
        """Verify 'T' (flake8-print) is in ruff.lint.select."""
        select = ruff_config["select"]
        assert "T" in select, "T (flake8-print) should be in Ruff select list"

    def test_tests_exempt_from_t201(self, ruff_config: dict[str, Any]) -> None:
        """Verify tests/**/*.py has T201 in per-file-ignores."""
        per_file_ignores = ruff_config["per-file-ignores"]
        test_ignores = per_file_ignores.get("tests/**/*.py", "")

        # T201 should be in the ignore list for tests
        assert "T201" in test_ignores, (
            "T201 should be ignored in tests/**/*.py - "
            "tests may use print for debugging"
        )

    def test_hook_scripts_exempt_from_t201(
        self,
        ruff_config: dict[str, Any],
    ) -> None:
        """Verify python-dev-framework/hooks/scripts/*.py has T201 in per-file-ignores."""
        per_file_ignores = ruff_config["per-file-ignores"]
        hook_ignores = per_file_ignores.get("python-dev-framework/hooks/scripts/*.py", "")

        # T201 should be in the ignore list for hooks
        # (they use print for stdout protocol)
        assert "T201" in hook_ignores, (
            "T201 should be ignored in hook scripts - "
            "hooks use print for stdout protocol"
        )

    def test_src_not_exempt_from_t201(self, ruff_config: dict[str, Any]) -> None:
        """Verify src/ directories are NOT exempt from T201."""
        per_file_ignores = ruff_config.get("per-file-ignores", {})

        # Check that no src/ pattern exempts T201
        for pattern, ignores in per_file_ignores.items():
            if "src" in pattern.lower():
                assert "T201" not in ignores, (
                    f"T201 should NOT be ignored in {pattern} - "
                    "src/ should use structlog, not print"
                )
