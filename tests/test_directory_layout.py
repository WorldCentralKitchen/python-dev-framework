"""Tests for TDD-005 directory layout enforcement via Ruff SLF001.

Note: SLF001 catches private ATTRIBUTE access (obj._private), not imports from
private modules. The _internal/ naming convention is documentation-based guidance.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# Add hooks/scripts to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent / "python-dev-framework" / "hooks" / "scripts")
)

from config import PluginConfig
from format_python import format_file


class TestSLF001Detection:
    """Tests for SLF001 rule detecting private attribute access violations."""

    def test_detects_private_attribute_access(self, tmp_path: Path) -> None:
        """SLF001 catches access to private attributes on objects."""
        test_file = tmp_path / "example.py"
        test_file.write_text(
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "class Foo:\n"
            "    _secret = 42\n"
            "\n"
            "\n"
            "x = Foo()._secret\n"
        )

        result = subprocess.run(
            ["uv", "run", "ruff", "check", "--select=SLF", str(test_file)],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0
        assert "SLF001" in result.stdout

    def test_detects_private_method_call(self, tmp_path: Path) -> None:
        """SLF001 catches calls to private methods on objects."""
        test_file = tmp_path / "example.py"
        test_file.write_text(
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "class Service:\n"
            "    def _internal_method(self) -> str:\n"
            '        return "internal"\n'
            "\n"
            "\n"
            "result = Service()._internal_method()\n"
        )

        result = subprocess.run(
            ["uv", "run", "ruff", "check", "--select=SLF", str(test_file)],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0
        assert "SLF001" in result.stdout

    def test_private_module_imports_not_detected(self, tmp_path: Path) -> None:
        """SLF001 does NOT catch imports from _internal modules (convention only)."""
        test_file = tmp_path / "example.py"
        test_file.write_text(
            "from __future__ import annotations\n"
            "from mypackage._internal.utils import helper\n"
        )

        result = subprocess.run(
            ["uv", "run", "ruff", "check", "--select=SLF", str(test_file)],
            capture_output=True,
            text=True,
            check=False,
        )

        # SLF001 does not catch module naming - this is convention-based only
        assert result.returncode == 0


class TestSLF001PerFileIgnores:
    """Tests for SLF001 per-file-ignores configuration."""

    def test_allows_internal_self_access(self, tmp_path: Path) -> None:
        """Internal modules can access their own private members."""
        # Create _internal directory structure
        internal_dir = tmp_path / "src" / "pkg" / "_internal"
        internal_dir.mkdir(parents=True)

        # Create utils.py with private function
        (internal_dir / "utils.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def _helper() -> str:\n"
            '    return "ok"\n'
        )

        # Create service.py that imports from utils
        service_file = internal_dir / "service.py"
        service_file.write_text(
            "from __future__ import annotations\n\nfrom .utils import _helper\n"
        )

        # Should pass when using per-file-ignores pattern
        result = subprocess.run(
            [
                "uv",
                "run",
                "ruff",
                "check",
                "--select=SLF",
                "--per-file-ignores",
                "src/*/_internal/*.py:SLF001",
                str(service_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0

    def test_allows_test_private_access(self, tmp_path: Path) -> None:
        """Test files can access private members via per-file-ignores."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_example.py"
        test_file.write_text(
            "from __future__ import annotations\n"
            "from mypackage._internal.utils import _helper\n"
        )

        result = subprocess.run(
            [
                "uv",
                "run",
                "ruff",
                "check",
                "--select=SLF",
                "--per-file-ignores",
                "tests/**/*.py:SLF001",
                str(test_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0


class TestSLF001InFormatHook:
    """Tests for SLF001 enforcement via format_python hook."""

    def test_strict_mode_runs_all_rules_including_slf(self) -> None:
        """Verify strict mode runs full ruff (includes SLF)."""

        config = PluginConfig(level="strict")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = str(mock_run.call_args_list[0])
            # Strict mode should NOT have --select restriction
            # This means all rules including SLF are active
            assert "--select=" not in ruff_call

    def test_moderate_mode_excludes_slf_rules(self) -> None:
        """Verify moderate mode uses core rules only (excludes SLF)."""
        config = PluginConfig(level="moderate")

        with patch("subprocess.run") as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = str(mock_run.call_args_list[0])
            # Moderate uses core rules + UP - SLF is NOT included
            assert "--select=E,W,F,I,B,UP" in ruff_call

    def test_minimal_mode_skips_ruff_entirely(self) -> None:
        """Verify minimal mode only runs black (no SLF enforcement)."""
        config = PluginConfig(level="minimal")

        with patch("subprocess.run") as mock_run:
            format_file("/path/to/file.py", config)

            # Should only call black (no ruff at all)
            assert mock_run.call_count == 1
            call_args = str(mock_run.call_args_list[0])
            assert "black" in call_args
            assert "ruff" not in call_args
