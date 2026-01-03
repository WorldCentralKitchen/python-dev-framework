"""Tests for git validation hook."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest


# Add hooks/scripts to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent / "python-dev-framework" / "hooks" / "scripts")
)

from config import PluginConfig
from validate_git import (
    build_branch_pattern,
    build_commit_pattern,
    extract_branch_name,
    extract_commit_message,
    extract_push_target,
    main,
    output_approve,
    output_block,
    read_stdin_context,
    validate_branch,
    validate_commit,
    validate_push,
)


class TestBranchPattern:
    def test_valid_feature_branch(self) -> None:
        pattern = build_branch_pattern(["feature", "bugfix"])
        assert pattern.match("feature/add-auth")

    def test_valid_bugfix_branch(self) -> None:
        pattern = build_branch_pattern(["feature", "bugfix"])
        assert pattern.match("bugfix/fix-login")

    def test_invalid_branch_no_type(self) -> None:
        pattern = build_branch_pattern(["feature", "bugfix"])
        assert not pattern.match("my-feature")

    def test_invalid_branch_wrong_type(self) -> None:
        pattern = build_branch_pattern(["feature", "bugfix"])
        assert not pattern.match("feat/add-auth")

    def test_invalid_branch_no_slash(self) -> None:
        pattern = build_branch_pattern(["feature", "bugfix"])
        assert not pattern.match("feature-add-auth")

    def test_invalid_branch_uppercase(self) -> None:
        pattern = build_branch_pattern(["feature", "bugfix"])
        assert not pattern.match("feature/Add-Auth")

    def test_valid_branch_with_numbers(self) -> None:
        pattern = build_branch_pattern(["feature", "bugfix"])
        assert pattern.match("feature/add-auth-123")


class TestCommitPattern:
    def test_valid_commit_with_scope(self) -> None:
        pattern = build_commit_pattern(["feat", "fix"])
        assert pattern.match("feat(auth): add login endpoint")

    def test_valid_commit_without_scope(self) -> None:
        pattern = build_commit_pattern(["feat", "fix"])
        assert pattern.match("feat: add login endpoint")

    def test_invalid_commit_no_colon(self) -> None:
        pattern = build_commit_pattern(["feat", "fix"])
        assert not pattern.match("feat add login")

    def test_invalid_commit_wrong_type(self) -> None:
        pattern = build_commit_pattern(["feat", "fix"])
        assert not pattern.match("feature(auth): add login")

    def test_valid_fix_commit(self) -> None:
        pattern = build_commit_pattern(["feat", "fix"])
        assert pattern.match("fix(api): handle null response")

    def test_valid_docs_commit(self) -> None:
        pattern = build_commit_pattern(["feat", "fix", "docs"])
        assert pattern.match("docs: update README")


class TestExtractBranchName:
    def test_checkout_b(self) -> None:
        cmd = "git checkout -b feature/add-auth"
        assert extract_branch_name(cmd) == "feature/add-auth"

    def test_switch_c(self) -> None:
        cmd = "git switch -c feature/add-auth"
        assert extract_branch_name(cmd) == "feature/add-auth"

    def test_no_branch_creation(self) -> None:
        cmd = "git checkout main"
        assert extract_branch_name(cmd) is None

    def test_git_status(self) -> None:
        cmd = "git status"
        assert extract_branch_name(cmd) is None

    def test_checkout_with_extra_args(self) -> None:
        cmd = "git checkout -b feature/add-auth origin/main"
        assert extract_branch_name(cmd) == "feature/add-auth"


class TestExtractCommitMessage:
    def test_single_quoted_message(self) -> None:
        cmd = "git commit -m 'feat(auth): add login'"
        assert extract_commit_message(cmd) == "feat(auth): add login"

    def test_double_quoted_message(self) -> None:
        cmd = 'git commit -m "feat(auth): add login"'
        assert extract_commit_message(cmd) == "feat(auth): add login"

    def test_commit_with_all_flag(self) -> None:
        cmd = 'git commit -am "fix: resolve bug"'
        assert extract_commit_message(cmd) == "fix: resolve bug"

    def test_no_message_flag(self) -> None:
        cmd = "git commit"
        assert extract_commit_message(cmd) is None

    def test_git_add_command(self) -> None:
        cmd = "git add ."
        assert extract_commit_message(cmd) is None

    def test_message_with_special_chars(self) -> None:
        cmd = 'git commit -m "fix(api): handle 404 errors"'
        assert extract_commit_message(cmd) == "fix(api): handle 404 errors"


class TestValidateBranch:
    def test_protected_branches_always_valid(self) -> None:
        config = PluginConfig(level="strict")
        for branch in ["main", "master", "develop"]:
            is_valid, error = validate_branch(branch, config)
            assert is_valid
            assert error is None

    def test_valid_feature_branch(self) -> None:
        config = PluginConfig()
        is_valid, error = validate_branch("feature/add-auth", config)
        assert is_valid
        assert error is None

    def test_invalid_branch_returns_error(self) -> None:
        config = PluginConfig()
        is_valid, error = validate_branch("bad-branch", config)
        assert not is_valid
        assert error is not None
        assert "type/description" in error


class TestValidateCommit:
    def test_valid_commit(self) -> None:
        config = PluginConfig()
        is_valid, error = validate_commit("feat(auth): add login", config)
        assert is_valid
        assert error is None

    def test_invalid_commit_returns_error(self) -> None:
        config = PluginConfig()
        is_valid, error = validate_commit("fixed stuff", config)
        assert not is_valid
        assert error is not None
        assert "type(scope): description" in error


class TestOutputFunctions:
    def test_output_approve(self, capsys: pytest.CaptureFixture[str]) -> None:
        output_approve()
        captured = capsys.readouterr()
        result = json.loads(captured.out.strip())
        assert result["decision"] == "approve"

    def test_output_block(self, capsys: pytest.CaptureFixture[str]) -> None:
        output_block("Invalid branch", "Use type/description")
        captured = capsys.readouterr()
        result = json.loads(captured.out.strip())
        assert result["decision"] == "block"
        assert result["reason"] == "Invalid branch"
        assert result["systemMessage"] == "Use type/description"


class TestReadStdinContext:
    def test_valid_json(self) -> None:
        input_data = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        with patch("sys.stdin", StringIO(input_data)):
            result = read_stdin_context()
            assert result["tool_name"] == "Bash"

    def test_invalid_json_returns_empty_dict(self) -> None:
        with patch("sys.stdin", StringIO("not json")):
            result = read_stdin_context()
            assert result == {}


class TestMain:
    def test_approves_non_bash_tools(self, capsys: pytest.CaptureFixture[str]) -> None:
        input_data = json.dumps({"tool_name": "Edit", "tool_input": {}})
        with patch("sys.stdin", StringIO(input_data)):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "approve"

    def test_approves_non_git_commands(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        with patch("sys.stdin", StringIO(input_data)):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "approve"

    def test_approves_valid_branch_strict(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b feature/add-auth"},
            }
        )
        strict_config = PluginConfig(level="strict")
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("validate_git.load_config", return_value=strict_config),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "approve"

    def test_blocks_invalid_branch_strict(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b bad-branch"},
            }
        )
        strict_config = PluginConfig(level="strict")
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("validate_git.load_config", return_value=strict_config),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "block"

    def test_approves_invalid_branch_moderate(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b bad-branch"},
            }
        )
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch(
                "validate_git.load_config", return_value=PluginConfig(level="moderate")
            ),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "approve"

    def test_approves_invalid_branch_minimal(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b bad-branch"},
            }
        )
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch(
                "validate_git.load_config", return_value=PluginConfig(level="minimal")
            ),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "approve"

    def test_approves_valid_commit_strict(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "feat(auth): add login"'},
            }
        )
        strict_config = PluginConfig(level="strict")
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("validate_git.load_config", return_value=strict_config),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "approve"

    def test_blocks_invalid_commit_strict(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "fixed stuff"'},
            }
        )
        strict_config = PluginConfig(level="strict")
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("validate_git.load_config", return_value=strict_config),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "block"

    def test_blocks_push_to_main_strict(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git push origin main"},
                "cwd": "/tmp",
            }
        )
        strict_config = PluginConfig(level="strict")
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("validate_git.load_config", return_value=strict_config),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "block"
            assert "Push blocked" in result["reason"]

    def test_blocks_push_to_master_strict(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git push origin master"},
                "cwd": "/tmp",
            }
        )
        strict_config = PluginConfig(level="strict")
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("validate_git.load_config", return_value=strict_config),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "block"

    def test_approves_push_to_feature_branch(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git push origin feature/add-auth"},
                "cwd": "/tmp",
            }
        )
        strict_config = PluginConfig(level="strict")
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("validate_git.load_config", return_value=strict_config),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "approve"

    def test_blocks_chained_push_to_main(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        'git add . && git commit -m "feat: x" && git push origin main'
                    )
                },
                "cwd": "/tmp",
            }
        )
        strict_config = PluginConfig(level="strict")
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch("validate_git.load_config", return_value=strict_config),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "block"

    def test_approves_push_to_main_moderate(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git push origin main"},
                "cwd": "/tmp",
            }
        )
        with (
            patch("sys.stdin", StringIO(input_data)),
            patch(
                "validate_git.load_config", return_value=PluginConfig(level="moderate")
            ),
        ):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out.strip())
            assert result["decision"] == "approve"


class TestExtractPushTarget:
    def test_push_with_remote_and_branch(self) -> None:

        remote, refspec = extract_push_target("git push origin main")
        assert remote == "origin"
        assert refspec == "main"

    def test_push_with_flags(self) -> None:

        remote, refspec = extract_push_target("git push -u origin feature/foo")
        assert remote == "origin"
        assert refspec == "feature/foo"

    def test_push_force(self) -> None:

        remote, refspec = extract_push_target("git push --force origin main")
        assert remote == "origin"
        assert refspec == "main"

    def test_bare_push(self) -> None:

        remote, refspec = extract_push_target("git push")
        assert remote is None
        assert refspec is None

    def test_push_in_chained_command(self) -> None:

        remote, refspec = extract_push_target("git add . && git push origin main")
        assert remote == "origin"
        assert refspec == "main"


class TestValidatePush:
    def test_push_to_main_blocked(self) -> None:

        is_valid, error = validate_push("main", "/tmp")
        assert not is_valid
        assert error is not None
        assert "protected branch" in error.lower()

    def test_push_to_master_blocked(self) -> None:

        is_valid, error = validate_push("master", "/tmp")
        assert not is_valid
        assert error is not None

    def test_push_to_feature_allowed(self) -> None:

        is_valid, error = validate_push("feature/add-auth", "/tmp")
        assert is_valid
        assert error is None

    def test_push_to_tag_allowed(self) -> None:

        is_valid, error = validate_push("v1.0.0", "/tmp")
        assert is_valid
        assert error is None

    def test_bare_push_on_feature_branch(self) -> None:

        with patch("validate_git.get_current_branch", return_value="feature/foo"):
            is_valid, _error = validate_push(None, "/tmp")
            assert is_valid

    def test_bare_push_on_main_blocked(self) -> None:

        with patch("validate_git.get_current_branch", return_value="main"):
            is_valid, _error = validate_push(None, "/tmp")
            assert not is_valid
