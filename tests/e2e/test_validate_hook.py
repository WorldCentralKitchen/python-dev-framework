"""E2E tests for PreToolUse git validation hook."""

from __future__ import annotations

from pathlib import Path

import pytest

from .helpers import run_git_via_claude


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
]


class TestValidateGitBranchE2E:
    """E2E tests for branch name validation."""

    def test_valid_branch_allowed_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """Valid branch name should be allowed in strict mode."""
        result = run_git_via_claude(
            project_dir=strict_settings,
            git_command="git checkout -b feature/add-auth",
        )

        assert result.succeeded, f"Valid branch blocked: {result.stderr}"
        assert not result.was_blocked

    def test_invalid_branch_blocked_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """Invalid branch name should be blocked in strict mode."""
        result = run_git_via_claude(
            project_dir=strict_settings,
            git_command="git checkout -b my-bad-branch",
        )

        # PreToolUse hook should block this
        assert (
            result.was_blocked or not result.succeeded
        ), f"Invalid branch allowed: stdout={result.stdout}, stderr={result.stderr}"

    def test_invalid_branch_allowed_moderate(
        self,
        moderate_settings: Path,
    ) -> None:
        """Invalid branch name should warn but allow in moderate mode."""
        result = run_git_via_claude(
            project_dir=moderate_settings,
            git_command="git checkout -b my-bad-branch",
        )

        # Should succeed (allowed with warning)
        assert result.succeeded, f"Branch creation failed: {result.stderr}"
        assert not result.was_blocked

    def test_invalid_branch_allowed_minimal(
        self,
        minimal_settings: Path,
    ) -> None:
        """Invalid branch name should be silently allowed in minimal mode."""
        result = run_git_via_claude(
            project_dir=minimal_settings,
            git_command="git checkout -b my-bad-branch",
        )

        assert result.succeeded, f"Branch creation failed: {result.stderr}"
        assert not result.was_blocked

    def test_protected_branches_always_allowed(
        self,
        strict_settings: Path,
    ) -> None:
        """Protected branches (main, master, develop) always allowed."""
        # Note: These branches might fail for other reasons (already exists, etc.)
        # but they should NOT be blocked by the validation hook
        for branch in ["develop"]:  # main already exists from git init
            result = run_git_via_claude(
                project_dir=strict_settings,
                git_command=f"git checkout -b {branch}",
            )

            # Should not be blocked by validation (may fail for other reasons)
            assert not result.was_blocked, f"Protected branch {branch} was blocked"

    def test_various_valid_branch_types(
        self,
        strict_settings: Path,
    ) -> None:
        """All configured branch types should be allowed."""
        branch_types = [
            "feature/new-feature",
            "bugfix/fix-issue",
            "hotfix/urgent-fix",
            "refactor/cleanup-code",
            "docs/update-readme",
            "test/add-tests",
            "chore/update-deps",
        ]

        for branch in branch_types:
            result = run_git_via_claude(
                project_dir=strict_settings,
                git_command=f"git checkout -b {branch}",
            )

            assert not result.was_blocked, f"Valid branch type blocked: {branch}"

            # Switch back to main for next iteration
            run_git_via_claude(strict_settings, "git checkout main")


class TestValidateGitCommitE2E:
    """E2E tests for commit message validation."""

    def test_valid_commit_allowed_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """Valid commit message should be allowed in strict mode."""
        project_dir = strict_settings

        # Create a file to commit
        test_file = project_dir / "test.txt"
        test_file.write_text("test content")

        # Stage the file first (without hook validation)
        run_git_via_claude(project_dir, "git add test.txt")

        # Commit with valid message
        result = run_git_via_claude(
            project_dir=project_dir,
            git_command='git commit -m "feat(auth): add login endpoint"',
        )

        assert result.succeeded, f"Valid commit blocked: {result.stderr}"
        assert not result.was_blocked

    def test_invalid_commit_blocked_strict(
        self,
        strict_settings: Path,
    ) -> None:
        """Invalid commit message should be blocked in strict mode."""
        project_dir = strict_settings

        # Create and stage a file
        test_file = project_dir / "test.txt"
        test_file.write_text("test content")
        run_git_via_claude(project_dir, "git add test.txt")

        # Commit with invalid message
        result = run_git_via_claude(
            project_dir=project_dir,
            git_command='git commit -m "fixed stuff"',
        )

        assert (
            result.was_blocked or not result.succeeded
        ), f"Invalid commit was allowed: {result.stdout}"

    def test_invalid_commit_allowed_moderate(
        self,
        moderate_settings: Path,
    ) -> None:
        """Invalid commit message should warn but allow in moderate mode."""
        project_dir = moderate_settings

        # Create and stage a file
        test_file = project_dir / "test.txt"
        test_file.write_text("test content")
        run_git_via_claude(project_dir, "git add test.txt")

        # Commit with invalid message
        result = run_git_via_claude(
            project_dir=project_dir,
            git_command='git commit -m "fixed stuff"',
        )

        assert result.succeeded, f"Commit failed: {result.stderr}"
        assert not result.was_blocked

    def test_various_valid_commit_types(
        self,
        strict_settings: Path,
    ) -> None:
        """All configured commit types should be allowed."""
        project_dir = strict_settings

        commit_types = [
            "feat(core): add new feature",
            "fix(api): resolve null error",
            "docs(readme): update installation",
            "style(lint): fix formatting",
            "refactor(auth): simplify logic",
            "perf(query): optimize database",
            "test(unit): add coverage",
            "build(deps): update packages",
            "ci(github): add workflow",
            "chore(release): bump version",
        ]

        for i, message in enumerate(commit_types):
            # Create and stage a unique file
            test_file = project_dir / f"test{i}.txt"
            test_file.write_text(f"content {i}")
            run_git_via_claude(project_dir, f"git add test{i}.txt")

            result = run_git_via_claude(
                project_dir=project_dir,
                git_command=f'git commit -m "{message}"',
            )

            assert not result.was_blocked, f"Valid commit type blocked: {message}"
