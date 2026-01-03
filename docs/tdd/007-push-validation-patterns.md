# TDD-007: Push Validation Patterns

| Field | Value |
|-------|-------|
| Version | 0.5.0 |
| Date | 2026-01-02 |
| Related ADRs | [ADR-002](../adr/002-two-layer-enforcement-model.md), [ADR-015](../adr/015-protected-branch-push-validation.md) |

## Overview

Implementation patterns for validating `git push` commands in the PreToolUse hook.

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
