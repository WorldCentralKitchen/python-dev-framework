"""Tests for Python formatting hook."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Add hooks/scripts to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent / "python-dev-framework" / "hooks" / "scripts")
)

from config import PluginConfig
from format_python import (
    check_dependencies,
    check_future_annotations,
    check_types,
    convert_py_version,
    format_file,
    get_ruff_rules,
    get_version_specific_ignores,
    main,
    output_block,
    read_stdin_context,
)


class TestCheckDependencies:
    def test_missing_uv(self) -> None:
        with patch("shutil.which", return_value=None):
            error = check_dependencies()
            assert error is not None
            assert "uv not found" in error

    def test_uv_present_ruff_missing(self) -> None:
        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/uv" if cmd == "uv" else None

        mock_result = MagicMock()
        mock_result.returncode = 1

        with (
            patch("shutil.which", side_effect=mock_which),
            patch("subprocess.run", return_value=mock_result),
        ):
            error = check_dependencies()
            assert error is not None
            assert "ruff not found" in error

    def test_all_present(self) -> None:
        def mock_which(cmd: str) -> str:
            return f"/usr/bin/{cmd}"

        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch("shutil.which", side_effect=mock_which),
            patch("subprocess.run", return_value=mock_result),
        ):
            error = check_dependencies()
            assert error is None


class TestFormatFile:
    def test_minimal_level_only_runs_black(self) -> None:
        config = PluginConfig(level="minimal")

        with patch("subprocess.run") as mock_run:
            result = format_file("/path/to/file.py", config)

            # Should only call black
            assert mock_run.call_count == 1
            call_args = mock_run.call_args_list[0][0][0]
            assert "black" in call_args
            # Minimal returns empty list (no lint check)
            assert result == []

    def test_moderate_level_runs_core_ruff_and_black_and_check(self) -> None:
        """Moderate mode: 2-pass ruff (fix then check) + black."""
        config = PluginConfig(level="moderate")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = format_file("/path/to/file.py", config)

            # Should call: ruff --fix, black, then ruff check (2-pass processing)
            assert mock_run.call_count == 3

            ruff_fix_call = mock_run.call_args_list[0][0][0]
            assert "ruff" in ruff_fix_call
            assert "--fix" in ruff_fix_call
            # TDD-004: moderate mode includes UP rules for type import fixes
            assert "--select=E,W,F,I,B,UP" in ruff_fix_call

            black_call = mock_run.call_args_list[1][0][0]
            assert "black" in black_call

            # Pass 2: ruff check without --fix
            ruff_check_call = mock_run.call_args_list[2][0][0]
            assert "ruff" in ruff_check_call
            assert "--fix" not in ruff_check_call
            assert "--select=E,W,F,I,B,UP" in ruff_check_call

            # Moderate returns empty list (warns only, doesn't block)
            assert result == []

    def test_moderate_level_warns_on_unfixable_errors(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Moderate mode outputs warnings to stderr for unfixable issues."""
        config = PluginConfig(level="moderate")

        def mock_subprocess_run(cmd: list[str], **kwargs: object) -> MagicMock:
            result = MagicMock()
            # Last call is the lint check - return an error
            if "--fix" not in cmd and "ruff" in cmd:
                result.returncode = 1
                result.stdout = (
                    "file.py:10:5: B006 Mutable argument default\nFound 1 error."
                )
            else:
                result.returncode = 0
                result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            result = format_file("/path/to/file.py", config)

            # Moderate mode returns empty list (doesn't block)
            assert result == []

            # But should have printed warning to stderr
            captured = capsys.readouterr()
            assert "Warning:" in captured.err
            assert "B006" in captured.err

    def test_strict_level_runs_full_ruff_and_black_and_lint_check(self) -> None:
        config = PluginConfig(level="strict")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = format_file("/path/to/file.py", config)

            # Should call: ruff --fix, black, then ruff check (for unfixable errors)
            assert mock_run.call_count == 3

            ruff_fix_call = mock_run.call_args_list[0][0][0]
            assert "ruff" in ruff_fix_call
            assert "--fix" in ruff_fix_call
            # Strict should not have --select restriction
            assert "--select=E,W,F,I,B" not in ruff_fix_call

            black_call = mock_run.call_args_list[1][0][0]
            assert "black" in black_call

            ruff_check_call = mock_run.call_args_list[2][0][0]
            assert "ruff" in ruff_check_call
            assert "--fix" not in ruff_check_call

            # No errors returned when ruff passes
            assert result == []

    def test_strict_level_returns_unfixable_errors(self) -> None:
        config = PluginConfig(level="strict")

        def mock_subprocess_run(cmd: list[str], **kwargs: object) -> MagicMock:
            result = MagicMock()
            # Last call is the lint check - return an error
            if "--fix" not in cmd and "ruff" in cmd:
                result.returncode = 1
                result.stdout = (
                    "file.py:10:5: SLF001 Private member accessed\nFound 1 error."
                )
            else:
                result.returncode = 0
                result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            result = format_file("/path/to/file.py", config)

            # Should return the SLF001 error
            assert len(result) == 1
            assert "SLF001" in result[0]


class TestReadStdinContext:
    def test_valid_json(self) -> None:
        input_data = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "x"}})
        with patch("sys.stdin", StringIO(input_data)):
            result = read_stdin_context()
            assert result["tool_name"] == "Edit"

    def test_invalid_json_returns_empty_dict(self) -> None:
        with patch("sys.stdin", StringIO("not json")):
            result = read_stdin_context()
            assert result == {}

    def test_empty_input_returns_empty_dict(self) -> None:
        with patch("sys.stdin", StringIO("")):
            result = read_stdin_context()
            assert result == {}


class TestMain:
    def test_skips_non_edit_write_tools(self) -> None:
        input_data = json.dumps({"tool_name": "Bash", "tool_input": {}})
        with (
            patch("sys.stdin", StringIO(input_data)),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 0

    def test_skips_non_python_files(self) -> None:
        input_data = json.dumps(
            {"tool_name": "Edit", "tool_input": {"file_path": "/path/to/file.txt"}}
        )
        with (
            patch("sys.stdin", StringIO(input_data)),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 0

    def test_skips_nonexistent_files(self, tmp_path: Path) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(tmp_path / "nonexistent.py")},
            }
        )
        with (
            patch("sys.stdin", StringIO(input_data)),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 0

    def test_warns_on_missing_dependencies(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")
        input_data = json.dumps(
            {"tool_name": "Edit", "tool_input": {"file_path": str(test_file)}}
        )
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("shutil.which", return_value=None),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            main()
        output = mock_stdout.getvalue()
        assert "block" in output
        assert "Missing dependency" in output

    def test_formats_python_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")
        input_data = json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": str(test_file)}}
        )

        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("shutil.which", return_value="/usr/bin/uv"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
            patch("format_python.load_config", return_value=PluginConfig()),
        ):
            main()
            # Should have called dependency checks + format commands
            assert mock_run.call_count >= 2


class TestT201Integration:
    """Tests for T201 print ban integration with format_file."""

    def test_strict_mode_runs_ruff_with_all_rules(self) -> None:
        """Verify strict mode runs ruff without --select filter (includes T201)."""
        config = PluginConfig(level="strict")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            format_file("/path/to/file.py", config)

            # Should call ruff --fix, black, then ruff check
            assert mock_run.call_count == 3
            ruff_call = str(mock_run.call_args_list[0])

            # Strict mode should NOT have --select restriction
            # This means all rules including T (flake8-print) are active
            assert "--select=" not in ruff_call

    def test_moderate_mode_uses_core_rules_without_t201(self) -> None:
        """Verify moderate mode uses core rules + UP (no T)."""
        config = PluginConfig(level="moderate")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            format_file("/path/to/file.py", config)

            # 2-pass: ruff --fix, black, then ruff check
            assert mock_run.call_count == 3
            ruff_call = str(mock_run.call_args_list[0])

            # Moderate uses core rules + UP - T201 is NOT included
            assert "--select=E,W,F,I,B,UP" in ruff_call

    def test_minimal_mode_skips_ruff_entirely(self) -> None:
        """Verify minimal mode only runs black, skipping ruff (and T201)."""
        config = PluginConfig(level="minimal")

        with patch("subprocess.run") as mock_run:
            format_file("/path/to/file.py", config)

            # Should only call black (no ruff)
            assert mock_run.call_count == 1
            call_args = str(mock_run.call_args_list[0])
            assert "black" in call_args
            assert "ruff" not in call_args


class TestCheckTypes:
    """Tests for mypy type checking functionality."""

    def test_skips_type_check_in_moderate_mode(self) -> None:
        config = PluginConfig(level="moderate")
        errors = check_types("/path/to/file.py", config)
        assert errors == []

    def test_skips_type_check_in_minimal_mode(self) -> None:
        config = PluginConfig(level="minimal")
        errors = check_types("/path/to/file.py", config)
        assert errors == []

    def test_runs_mypy_in_strict_mode(self) -> None:
        config = PluginConfig(level="strict")

        # Mock mypy available and returning no errors
        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_mypy = MagicMock()
        mock_mypy.returncode = 0
        mock_mypy.stdout = ""

        with patch("subprocess.run", side_effect=[mock_version, mock_mypy]):
            errors = check_types("/path/to/file.py", config)
            assert errors == []

    def test_returns_mypy_not_found_error(self) -> None:
        config = PluginConfig(level="strict")

        mock_version = MagicMock()
        mock_version.returncode = 1  # mypy not found

        with patch("subprocess.run", return_value=mock_version):
            errors = check_types("/path/to/file.py", config)
            assert len(errors) == 1
            assert "mypy not found" in errors[0]

    def test_returns_type_errors(self) -> None:
        config = PluginConfig(level="strict")

        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_mypy = MagicMock()
        mock_mypy.returncode = 1
        mock_mypy.stdout = (
            "file.py:1: error: Missing return statement [return]\n"
            "file.py:5: error: Incompatible types [assignment]\n"
            "Found 2 errors in 1 file (checked 1 source file)"
        )

        with patch("subprocess.run", side_effect=[mock_version, mock_mypy]):
            errors = check_types("/path/to/file.py", config)
            assert len(errors) == 2
            assert "Missing return statement" in errors[0]
            assert "Incompatible types" in errors[1]


class TestCheckFutureAnnotations:
    """Tests for __future__ annotations checking."""

    def test_present_at_top(self, tmp_path: Path) -> None:
        """Passes when __future__ import is present."""
        test_file = tmp_path / "test.py"
        test_file.write_text("from __future__ import annotations\n\ndef foo(): pass")

        ok, error = check_future_annotations(test_file)
        assert ok is True
        assert error is None

    def test_missing(self, tmp_path: Path) -> None:
        """Fails when __future__ import is missing."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        ok, error = check_future_annotations(test_file)
        assert ok is False
        assert error is not None
        assert "from __future__ import annotations" in error

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty files pass (nothing to enforce)."""
        test_file = tmp_path / "test.py"
        test_file.write_text("")

        ok, error = check_future_annotations(test_file)
        assert ok is True
        assert error is None

    def test_only_comments(self, tmp_path: Path) -> None:
        """Files with only comments pass."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# This is a comment\n# Another comment\n")

        ok, error = check_future_annotations(test_file)
        assert ok is True
        assert error is None

    def test_present_after_docstring(self, tmp_path: Path) -> None:
        """Passes when __future__ import is after module docstring."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            '"""Module docstring."""\nfrom __future__ import annotations\n'
        )

        ok, error = check_future_annotations(test_file)
        assert ok is True
        assert error is None

    def test_shebang_and_encoding(self, tmp_path: Path) -> None:
        """Passes with shebang and encoding declaration."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "#!/usr/bin/env python3\n"
            "# -*- coding: utf-8 -*-\n"
            "from __future__ import annotations\n"
            "\ndef foo(): pass\n"
        )

        ok, error = check_future_annotations(test_file)
        assert ok is True
        assert error is None


class TestGetVersionSpecificIgnores:
    """Tests for version-specific Ruff ignores."""

    def test_py39_ignores_up036(self) -> None:
        """Python 3.9 should ignore UP036 (match statement)."""
        ignores = get_version_specific_ignores("py39")
        assert "UP036" in ignores

    def test_py310_no_ignores(self) -> None:
        """Python 3.10 has no version-specific ignores."""
        ignores = get_version_specific_ignores("py310")
        assert ignores == []

    def test_py312_no_ignores(self) -> None:
        """Python 3.12 has no version-specific ignores."""
        ignores = get_version_specific_ignores("py312")
        assert ignores == []


class TestGetRuffRules:
    """Tests for version-specific Ruff rules."""

    def test_py39_includes_fa(self) -> None:
        """Python 3.9 should include FA rules."""
        rules = get_ruff_rules("py39")
        assert "FA" in rules

    def test_py310_includes_fa(self) -> None:
        """Python 3.10 should include FA rules."""
        rules = get_ruff_rules("py310")
        assert "FA" in rules

    def test_py311_no_fa(self) -> None:
        """Python 3.11+ doesn't need FA rules."""
        rules = get_ruff_rules("py311")
        assert rules == []

    def test_py312_no_fa(self) -> None:
        """Python 3.12 doesn't need FA rules."""
        rules = get_ruff_rules("py312")
        assert rules == []


class TestConvertPyVersion:
    """Tests for Python version string conversion."""

    def test_py39_to_3_9(self) -> None:
        """Convert py39 to 3.9."""
        assert convert_py_version("py39") == "3.9"

    def test_py310_to_3_10(self) -> None:
        """Convert py310 to 3.10."""
        assert convert_py_version("py310") == "3.10"

    def test_py311_to_3_11(self) -> None:
        """Convert py311 to 3.11."""
        assert convert_py_version("py311") == "3.11"

    def test_py312_to_3_12(self) -> None:
        """Convert py312 to 3.12."""
        assert convert_py_version("py312") == "3.12"

    def test_py313_to_3_13(self) -> None:
        """Convert py313 to 3.13."""
        assert convert_py_version("py313") == "3.13"


class TestOutputBlock:
    """Tests for output_block helper."""

    def test_outputs_json_block(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Outputs correct JSON format."""
        output_block("Test error message")
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["decision"] == "block"
        assert result["reason"] == "Test error message"


class TestFormatFileVersionAware:
    """Tests for version-aware format_file behavior."""

    def test_passes_target_version_to_ruff_strict(self) -> None:
        """Strict mode passes --target-version to ruff."""
        config = PluginConfig(level="strict", target_python="py39")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = mock_run.call_args_list[0][0][0]
            assert "--target-version" in ruff_call
            assert "py39" in ruff_call

    def test_passes_target_version_to_ruff_moderate(self) -> None:
        """Moderate mode passes --target-version to ruff."""
        config = PluginConfig(level="moderate", target_python="py310")

        with patch("subprocess.run") as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = mock_run.call_args_list[0][0][0]
            assert "--target-version" in ruff_call
            assert "py310" in ruff_call

    def test_strict_includes_version_specific_ignores(self) -> None:
        """Strict mode includes version-specific ignores for py39."""
        config = PluginConfig(level="strict", target_python="py39")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = mock_run.call_args_list[0][0][0]
            assert "--ignore" in ruff_call
            assert "UP036" in ruff_call

    def test_strict_includes_fa_rules_for_py39(self) -> None:
        """Strict mode includes FA rules for py39."""
        config = PluginConfig(level="strict", target_python="py39")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = mock_run.call_args_list[0][0][0]
            assert "--extend-select" in ruff_call
            assert "FA" in ruff_call

    def test_strict_no_fa_rules_for_py312(self) -> None:
        """Strict mode doesn't add FA rules for py312."""
        config = PluginConfig(level="strict", target_python="py312")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = mock_run.call_args_list[0][0][0]
            assert "--extend-select" not in ruff_call


class TestCheckTypesVersionAware:
    """Tests for version-aware check_types behavior."""

    def test_passes_python_version_to_mypy(self) -> None:
        """Mypy receives --python-version flag."""
        config = PluginConfig(level="strict", target_python="py39")

        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_mypy = MagicMock()
        mock_mypy.returncode = 0
        mock_mypy.stdout = ""

        with patch("subprocess.run", side_effect=[mock_version, mock_mypy]) as mock_run:
            check_types("/path/to/file.py", config)

            mypy_call = mock_run.call_args_list[1][0][0]
            assert "--python-version" in mypy_call
            assert "3.9" in mypy_call

    def test_passes_py312_version_to_mypy(self) -> None:
        """Mypy receives correct version for py312."""
        config = PluginConfig(level="strict", target_python="py312")

        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_mypy = MagicMock()
        mock_mypy.returncode = 0
        mock_mypy.stdout = ""

        with patch("subprocess.run", side_effect=[mock_version, mock_mypy]) as mock_run:
            check_types("/path/to/file.py", config)

            mypy_call = mock_run.call_args_list[1][0][0]
            assert "--python-version" in mypy_call
            assert "3.12" in mypy_call


class TestTypeImportRules:
    """Tests for TDD-004 type import enforcement via Ruff rules."""

    def test_strict_mode_includes_up_and_tch_rules(self) -> None:
        """Strict mode runs full ruff (includes UP and TCH)."""
        config = PluginConfig(level="strict")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = str(mock_run.call_args_list[0])
            # No --select means all rules including UP and TCH
            assert "--select=" not in ruff_call

    def test_moderate_mode_includes_up_rules(self) -> None:
        """Moderate mode includes UP rules for type import fixes."""
        config = PluginConfig(level="moderate")

        with patch("subprocess.run") as mock_run:
            format_file("/path/to/file.py", config)

            ruff_call = str(mock_run.call_args_list[0])
            assert "--select=E,W,F,I,B,UP" in ruff_call

    def test_minimal_mode_excludes_type_import_rules(self) -> None:
        """Minimal mode only runs black - no UP or TCH."""
        config = PluginConfig(level="minimal")

        with patch("subprocess.run") as mock_run:
            format_file("/path/to/file.py", config)

            assert mock_run.call_count == 1
            call_args = str(mock_run.call_args_list[0])
            assert "black" in call_args
            assert "ruff" not in call_args
