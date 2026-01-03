"""Tests for configuration loader."""

from __future__ import annotations

import json
import os

# Add hooks/scripts to path for imports
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest


sys.path.insert(
    0, str(Path(__file__).parent.parent / "python-dev-framework" / "hooks" / "scripts")
)

from config import (
    DEFAULT_BRANCH_TYPES,
    DEFAULT_COMMIT_TYPES,
    PluginConfig,
    detect_python_version,
    load_config,
)


if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project directory with .claude folder."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(tmp_path)}):
        yield tmp_path


class TestPluginConfig:
    def test_default_values(self):
        config = PluginConfig()
        assert config.level == "strict"
        assert config.branch_types == DEFAULT_BRANCH_TYPES
        assert config.commit_types == DEFAULT_COMMIT_TYPES

    def test_custom_level(self):
        config = PluginConfig(level="moderate")
        assert config.level == "moderate"

    def test_custom_branch_types(self):
        custom_types = ["feature", "fix"]
        config = PluginConfig(branch_types=custom_types)
        assert config.branch_types == custom_types


class TestLoadConfig:
    def test_missing_settings_file_returns_defaults(
        self, temp_project_dir: Path
    ) -> None:
        # Fixture sets CLAUDE_PROJECT_DIR env var; settings.json doesn't exist
        _ = temp_project_dir  # Used by fixture for env setup
        config = load_config()
        assert config.level == "strict"
        assert config.branch_types == DEFAULT_BRANCH_TYPES

    def test_empty_settings_returns_defaults(self, temp_project_dir: Path) -> None:
        settings_path = temp_project_dir / ".claude" / "settings.json"
        settings_path.write_text("{}")

        config = load_config()
        assert config.level == "strict"

    def test_valid_strict_level(self, temp_project_dir: Path) -> None:
        settings_path = temp_project_dir / ".claude" / "settings.json"
        settings_path.write_text(
            json.dumps({"plugins": {"python-dev-framework": {"level": "strict"}}})
        )

        config = load_config()
        assert config.level == "strict"

    def test_valid_moderate_level(self, temp_project_dir: Path) -> None:
        settings_path = temp_project_dir / ".claude" / "settings.json"
        settings_path.write_text(
            json.dumps({"plugins": {"python-dev-framework": {"level": "moderate"}}})
        )

        config = load_config()
        assert config.level == "moderate"

    def test_valid_minimal_level(self, temp_project_dir: Path) -> None:
        settings_path = temp_project_dir / ".claude" / "settings.json"
        settings_path.write_text(
            json.dumps({"plugins": {"python-dev-framework": {"level": "minimal"}}})
        )

        config = load_config()
        assert config.level == "minimal"

    def test_invalid_level_defaults_to_strict(self, temp_project_dir: Path) -> None:
        settings_path = temp_project_dir / ".claude" / "settings.json"
        settings_path.write_text(
            json.dumps({"plugins": {"python-dev-framework": {"level": "invalid"}}})
        )

        config = load_config()
        assert config.level == "strict"

    def test_custom_branch_types(self, temp_project_dir: Path) -> None:
        settings_path = temp_project_dir / ".claude" / "settings.json"
        custom_types = ["feature", "bugfix"]
        settings_path.write_text(
            json.dumps(
                {"plugins": {"python-dev-framework": {"branch_types": custom_types}}}
            )
        )

        config = load_config()
        assert config.branch_types == custom_types

    def test_custom_commit_types(self, temp_project_dir: Path) -> None:
        settings_path = temp_project_dir / ".claude" / "settings.json"
        custom_types = ["feat", "fix"]
        settings_path.write_text(
            json.dumps(
                {"plugins": {"python-dev-framework": {"commit_types": custom_types}}}
            )
        )

        config = load_config()
        assert config.commit_types == custom_types

    def test_invalid_json_returns_defaults(self, temp_project_dir: Path) -> None:
        settings_path = temp_project_dir / ".claude" / "settings.json"
        settings_path.write_text("not valid json")

        config = load_config()
        assert config.level == "strict"

    def test_no_project_dir_env_uses_current_dir(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            config = load_config()
            assert config.level == "strict"


class TestDetectPythonVersion:
    """Tests for Python version detection from pyproject.toml."""

    def test_detect_from_ruff_target_version(self, tmp_path: Path) -> None:
        """Priority 1: ruff target-version."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.ruff]\ntarget-version = "py39"')

        assert detect_python_version(tmp_path) == "py39"

    def test_detect_from_requires_python(self, tmp_path: Path) -> None:
        """Priority 2: project.requires-python."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nrequires-python = ">=3.10"')

        assert detect_python_version(tmp_path) == "py310"

    def test_ruff_priority_over_requires(self, tmp_path: Path) -> None:
        """Ruff target-version should win over requires-python."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
requires-python = ">=3.10"

[tool.ruff]
target-version = "py39"
"""
        )

        assert detect_python_version(tmp_path) == "py39"

    def test_default_no_pyproject(self, tmp_path: Path) -> None:
        """Default to py312 when no pyproject.toml."""
        assert detect_python_version(tmp_path) == "py312"

    def test_default_no_version_specified(self, tmp_path: Path) -> None:
        """Default to py312 when pyproject exists but no version."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"')

        assert detect_python_version(tmp_path) == "py312"

    def test_requires_python_with_space(self, tmp_path: Path) -> None:
        """Handle requires-python with spaces."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nrequires-python = ">= 3.9"')

        assert detect_python_version(tmp_path) == "py39"

    def test_requires_python_with_upper_bound(self, tmp_path: Path) -> None:
        """Handle requires-python with upper bound."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nrequires-python = ">=3.9,<3.13"')

        assert detect_python_version(tmp_path) == "py39"

    def test_requires_python_tilde_equals(self, tmp_path: Path) -> None:
        """Handle requires-python with ~= operator."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nrequires-python = "~=3.10"')

        assert detect_python_version(tmp_path) == "py310"

    def test_detect_py311(self, tmp_path: Path) -> None:
        """Correctly parse Python 3.11."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.ruff]\ntarget-version = "py311"')

        assert detect_python_version(tmp_path) == "py311"

    def test_detect_py312(self, tmp_path: Path) -> None:
        """Correctly parse Python 3.12."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.ruff]\ntarget-version = "py312"')

        assert detect_python_version(tmp_path) == "py312"

    def test_detect_py313(self, tmp_path: Path) -> None:
        """Correctly parse Python 3.13."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.ruff]\ntarget-version = "py313"')

        assert detect_python_version(tmp_path) == "py313"

    def test_invalid_toml_returns_default(self, tmp_path: Path) -> None:
        """Invalid TOML returns default py312."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("not valid toml [[[")

        assert detect_python_version(tmp_path) == "py312"


class TestLoadConfigWithVersion:
    """Tests for load_config with Python version detection."""

    def test_loads_target_python_from_pyproject(self, tmp_path: Path) -> None:
        """load_config should include detected target_python."""
        # Create pyproject.toml with ruff target
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.ruff]\ntarget-version = "py39"')

        # Create .claude directory and settings
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(tmp_path)}):
            config = load_config(tmp_path)

        assert config.target_python == "py39"

    def test_default_target_python_when_no_pyproject(
        self, temp_project_dir: Path
    ) -> None:
        """load_config defaults to py312 when no pyproject.toml."""
        config = load_config(temp_project_dir)
        assert config.target_python == "py312"

    def test_target_python_with_settings(self, tmp_path: Path) -> None:
        """target_python works with custom settings.json."""
        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nrequires-python = ">=3.10"')

        # Create settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(
            json.dumps({"plugins": {"python-dev-framework": {"level": "moderate"}}})
        )

        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(tmp_path)}):
            config = load_config(tmp_path)

        assert config.level == "moderate"
        assert config.target_python == "py310"
