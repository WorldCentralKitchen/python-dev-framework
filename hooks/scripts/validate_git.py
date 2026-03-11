#!/usr/bin/env python3
"""Validate git branch names and commit messages.

PreToolUse hook that intercepts Bash commands containing git operations.
Behavior varies by strictness level.

Note: PreToolUse hooks can block operations before execution using deny().
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


# Ensure script directory is in path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))

from config import PluginConfig, load_config


def build_branch_pattern(branch_types: list[str]) -> re.Pattern[str]:
    """Build regex pattern for valid branch names."""
    types_pattern = "|".join(re.escape(t) for t in branch_types)
    return re.compile(rf"^({types_pattern})/[a-z0-9.-]+$")


def build_commit_pattern(commit_types: list[str]) -> re.Pattern[str]:
    """Build regex pattern for valid commit messages."""
    types_pattern = "|".join(re.escape(t) for t in commit_types)
    return re.compile(rf"^({types_pattern})(\(.+\))?: .+")


def extract_branch_name(command: str) -> str | None:
    """Extract branch name from git checkout -b or git switch -c command."""
    match = re.search(r"git\s+(checkout\s+-b|switch\s+-c)\s+(\S+)", command)
    return match.group(2) if match else None


def extract_commit_message(command: str) -> str | None:
    """Extract commit message from git commit -m command.

    Handles both single and double quoted messages, including heredoc patterns.
    Also handles combined flags like -am.
    """
    # Handle heredoc pattern: git commit -m "$(cat <<'EOF' ... EOF)"
    heredoc_match = re.search(
        r"git\s+commit.*-m\s+\"\$\(cat\s+<<['\"]?EOF['\"]?\s*\n(.+?)\nEOF",
        command,
        re.DOTALL,
    )
    if heredoc_match:
        return heredoc_match.group(1).strip().split("\n")[0]

    # Handle simple quoted messages (including combined flags like -am)
    match = re.search(r'git\s+commit\s+(?:-[a-z]*m|-m)\s+["\']([^"\']+)["\']', command)
    return match.group(1) if match else None


def read_stdin_context() -> dict[str, Any]:
    """Read hook context from stdin."""
    try:
        return json.loads(sys.stdin.read())  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {}


def output_block(reason: str, system_message: str) -> None:
    """Output block response."""
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": reason,
                "systemMessage": system_message,
            }
        )
    )


def output_approve() -> None:
    """Output approve response."""
    print(json.dumps({"decision": "approve"}))


def suggest_branch_type(branch: str, valid_types: list[str]) -> str | None:
    """Suggest the closest valid branch type for a mistyped branch.

    Returns the suggested corrected branch name, or None.
    """
    if "/" not in branch:
        return None

    used_type, description = branch.split("/", 1)

    # Common aliases/mistakes mapped to valid types
    aliases: dict[str, str] = {
        "fix": "bugfix",
        "bug": "bugfix",
        "feat": "feature",
        "hot": "hotfix",
        "ref": "refactor",
        "doc": "docs",
        "tests": "test",
        "testing": "test",
    }

    suggested = aliases.get(used_type)
    if suggested and suggested in valid_types:
        return f"{suggested}/{description}"

    # Check prefix match (e.g., "fea" -> "feature")
    for valid_type in valid_types:
        if valid_type.startswith(used_type) and used_type != valid_type:
            return f"{valid_type}/{description}"

    return None


def validate_branch(branch: str, config: PluginConfig) -> tuple[bool, str | None]:
    """Validate branch name against pattern.

    Returns (is_valid, error_message).
    """
    # Allow protected branches (and develop for common workflow)
    if branch in config.protected_branches or branch == "develop":
        return True, None

    pattern = build_branch_pattern(config.branch_types)
    if pattern.match(branch):
        return True, None

    valid_types = ", ".join(config.branch_types)
    message = f"Use format: type/description where type is one of: {valid_types}"

    suggestion = suggest_branch_type(branch, config.branch_types)
    if suggestion:
        message += f". Did you mean: {suggestion}"

    return False, message


def validate_commit(message: str, config: PluginConfig) -> tuple[bool, str | None]:
    """Validate commit message against pattern.

    Returns (is_valid, error_message).
    """
    pattern = build_commit_pattern(config.commit_types)
    if pattern.match(message):
        return True, None

    valid_types = ", ".join(config.commit_types)
    guidance = (
        f"Use format: type(scope): description where type is one of: {valid_types}"
    )
    return False, guidance


def get_current_branch(cwd: str) -> str | None:
    """Get current git branch name."""

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def extract_push_target(command: str) -> tuple[str | None, str | None]:
    """Extract remote and refspec from git push command.

    Returns (remote, refspec) tuple. Either may be None.
    """
    match = re.search(
        r"git\s+push"
        r"(?:\s+[-][-]?\S+)*"  # optional flags
        r"(?:\s+(\S+))?"  # optional remote
        r"(?:\s+(\S+))?",  # optional refspec
        command,
    )
    if not match:
        return None, None
    return match.group(1), match.group(2)


def parse_refspec_destination(refspec: str) -> str:
    """Extract destination branch from refspec.

    Handles formats: 'branch', 'src:dst', 'HEAD:dst', '+src:dst'
    """
    # Remove leading + (force push indicator)
    spec = refspec.lstrip("+")

    # If contains colon, destination is after the colon
    if ":" in spec:
        return spec.split(":", 1)[1]

    # Otherwise the refspec itself is the branch
    return spec


def validate_push(
    refspec: str | None, cwd: str, config: PluginConfig
) -> tuple[bool, str | None]:
    """Validate push target.

    Returns (is_valid, error_message).
    """
    # Determine target branch
    target: str | None = None

    if refspec is not None:
        target = parse_refspec_destination(refspec)
    else:
        # Bare push - check current branch
        target = get_current_branch(cwd)

    if target is None:
        return True, None  # Can't determine, allow

    # Check if pushing to protected branch
    if target in config.protected_branches:
        return False, "Direct push to protected branch. Create a PR instead."

    return True, None


def contains_gh_pr_merge(command: str) -> bool:
    """Check if command contains gh pr merge."""
    return bool(re.search(r"\bgh\s+pr\s+merge\b", command))


def validate_gh_merge(command: str) -> tuple[bool, str | None]:
    """Validate gh pr merge command.

    Always returns invalid - PR merges require human approval.
    Returns (is_valid, error_message).
    """
    if contains_gh_pr_merge(command):
        return False, "PR merges require human approval. Review and merge manually."
    return True, None


def handle_validation_result(
    is_valid: bool,
    error_message: str | None,
    block_reason: str,
    config: PluginConfig,
) -> bool:
    """Handle validation result based on strictness level.

    Returns True if execution should stop (blocked in strict mode).
    """
    if is_valid:
        return False

    if config.level == "strict":
        output_block(block_reason, error_message or "")
        return True
    elif config.level == "moderate":
        print(f"Warning: {error_message}", file=sys.stderr)

    return False


def main() -> None:
    """Hook entry point."""
    context = read_stdin_context()

    tool_name = context.get("tool_name", "")
    tool_input = context.get("tool_input", {})

    # Verify tool type (defense in depth beyond hooks.json matcher)
    if tool_name != "Bash":
        output_approve()
        return

    command = tool_input.get("command", "")

    # Skip commands that don't involve git or gh
    if "git" not in command and "gh" not in command:
        output_approve()
        return

    config = load_config()

    # Check branch creation
    if branch := extract_branch_name(command):
        is_valid, error_message = validate_branch(branch, config)
        if handle_validation_result(
            is_valid, error_message, f"Invalid branch: {branch}", config
        ):
            return

    # Check commit message
    if message := extract_commit_message(command):
        is_valid, error_message = validate_commit(message, config)
        if handle_validation_result(
            is_valid, error_message, f"Invalid commit message: {message}", config
        ):
            return

    # Check push to protected branch
    if "git push" in command:
        _remote, refspec = extract_push_target(command)
        cwd = context.get("cwd", ".")
        is_valid, error_message = validate_push(refspec, cwd, config)
        if handle_validation_result(is_valid, error_message, "Push blocked", config):
            return

    # Check gh pr merge (requires human approval)
    if "gh" in command and "merge" in command:
        is_valid, error_message = validate_gh_merge(command)
        if handle_validation_result(
            is_valid, error_message, "PR merge blocked", config
        ):
            return

    output_approve()


if __name__ == "__main__":
    main()
