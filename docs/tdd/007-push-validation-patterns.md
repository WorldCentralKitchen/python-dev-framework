# TDD-007: Protected Branch Enforcement Patterns

| Field | Value |
|-------|-------|
| Version | 0.6.0 |
| Date | 2026-01-02 |
| Related ADRs | [ADR-002](../adr/002-two-layer-enforcement-model.md), [ADR-015](../adr/015-protected-branch-push-validation.md) |

## Overview

Implementation patterns for validating `git push` and `gh pr merge` commands in the PreToolUse hook.

---

## Part 1: Push Validation (v0.5.0)

## Command Parsing

### Regex Pattern

```python
PUSH_PROTECTED_PATTERN = re.compile(
    r"git\s+push"              # git push
    r"(?:\s+[-][-]?\S+)*"      # optional flags (--force, -u, etc.)
    r"(?:\s+\S+)?"             # optional remote (origin)
    r"\s+(main|master)\b"      # protected branch name
)
```

### Extraction Function

```python
def extract_push_target(command: str) -> tuple[str | None, str | None]:
    """Extract remote and refspec from git push command.

    Returns (remote, refspec) tuple. Either may be None.
    """
    # Match git push with optional flags, remote, and refspec
    match = re.search(
        r"git\s+push"
        r"(?:\s+[-][-]?\S+)*"      # flags
        r"(?:\s+(\S+))?"           # remote
        r"(?:\s+(\S+))?",          # refspec
        command
    )
    if not match:
        return None, None
    return match.group(1), match.group(2)
```

## Current Branch Detection

For bare `git push` (no refspec), check current branch:

```python
def get_current_branch(cwd: str) -> str | None:
    """Get current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None
```

## Validation Logic

```python
PROTECTED_BRANCHES = frozenset({"main", "master"})

def validate_push(
    remote: str | None,
    refspec: str | None,
    cwd: str,
) -> tuple[bool, str | None]:
    """Validate push target.

    Returns (is_valid, error_message).
    """
    # Determine target branch
    if refspec:
        target = refspec
    else:
        # Bare push - check current branch
        target = get_current_branch(cwd)
        if target is None:
            return True, None  # Can't determine, allow

    # Check if pushing to protected branch
    if target in PROTECTED_BRANCHES:
        return False, "Direct push to protected branch. Create a PR instead."

    return True, None
```

## Integration in main()

```python
# After commit validation, before output_approve():
if "git push" in command:
    remote, refspec = extract_push_target(command)
    cwd = context.get("cwd", ".")
    is_valid, error_message = validate_push(remote, refspec, cwd)
    if not is_valid:
        if config.level == "strict":
            output_block("Push blocked", error_message or "")
            return
        elif config.level == "moderate":
            print(f"Warning: {error_message}", file=sys.stderr)
```

## Test Cases

### Unit Tests

| Input | Remote | Refspec | Expected |
|-------|--------|---------|----------|
| `git push origin main` | `origin` | `main` | Block |
| `git push origin master` | `origin` | `master` | Block |
| `git push -u origin main` | `origin` | `main` | Block |
| `git push --force origin main` | `origin` | `main` | Block |
| `git push origin feature/foo` | `origin` | `feature/foo` | Allow |
| `git push origin v1.0.0` | `origin` | `v1.0.0` | Allow |
| `git push` | `None` | `None` | Check current branch |

### Chained Commands

| Input | Expected |
|-------|----------|
| `git add . && git push origin main` | Block |
| `git commit -m "x" && git push origin main` | Block |
| `echo "done" && git push origin feature/x` | Allow |

### E2E Test

```python
def test_push_to_main_blocked(e2e_project, strict_settings):
    """Push to main should be blocked in strict mode."""
    result = run_claude(
        e2e_project,
        "Run: git push origin main",
    )
    assert "blocked" in result.lower() or "create a pr" in result.lower()
```

---

## Part 2: PR Merge Validation (v0.6.0)

### Command Detection

Detect `gh pr merge` commands anywhere in the Bash command string:

```python
def contains_gh_pr_merge(command: str) -> bool:
    """Check if command contains gh pr merge."""
    return bool(re.search(r"\bgh\s+pr\s+merge\b", command))
```

### Validation Function

```python
def validate_gh_merge(command: str) -> tuple[bool, str | None]:
    """Validate gh pr merge command.

    Always returns invalid - PR merges require human approval.
    Returns (is_valid, error_message).
    """
    if contains_gh_pr_merge(command):
        return False, "PR merges require human approval. Review and merge manually."
    return True, None
```

### Integration in main()

```python
# After push validation, before output_approve():
if "gh" in command and "merge" in command:
    is_valid, error_message = validate_gh_merge(command)
    if handle_validation_result(
        is_valid, error_message, "PR merge blocked", config
    ):
        return
```

### Test Cases

#### Unit Tests

| Input | Expected |
|-------|----------|
| `gh pr merge 123` | Block |
| `gh pr merge 123 --squash` | Block |
| `gh pr merge --squash --delete-branch` | Block |
| `gh pr merge 123 --auto` | Block |
| `gh pr merge` | Block |
| `gh pr create` | Allow |
| `gh pr view 123` | Allow |
| `gh pr list` | Allow |

#### Chained Commands

| Input | Expected |
|-------|----------|
| `gh pr create && gh pr merge` | Block |
| `echo "done" && gh pr merge 123` | Block |
| `gh pr create --fill` | Allow |

#### E2E Test

```python
def test_gh_pr_merge_blocked_strict(strict_settings):
    """gh pr merge should be blocked in strict mode."""
    result = run_git_via_claude(
        project_dir=strict_settings,
        git_command="gh pr merge 123 --squash",
    )
    assert result.was_blocked or not result.succeeded

def test_gh_pr_merge_allowed_moderate(moderate_settings):
    """gh pr merge should warn but allow in moderate mode."""
    result = run_git_via_claude(
        project_dir=moderate_settings,
        git_command="gh pr merge 123 --squash",
    )
    assert not result.was_blocked
```
