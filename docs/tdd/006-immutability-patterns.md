# TDD-006: Immutability Pattern Enforcement

| Field | Value |
|-------|-------|
| Version | 0.2.0 |
| Date | 2025-12-29 |
| Related ADRs | [ADR-013](../adr/013-immutability-safety-patterns.md) |

## Overview

How the plugin enforces immutability patterns through Ruff rules, mypy, and prescribed dependencies.

## Enforcement Strategy

| Pattern                     | Enforcement       | Mechanism           |
| --------------------------- | ----------------- | ------------------- |
| Mutable argument defaults   | **Detect + Block**| Ruff B006 (unsafe fix¹) |
| Mutable contextvar defaults | **Automated**     | Ruff B039           |
| Mutable dataclass defaults  | **Detect + Block**| Ruff RUF008 (no fix)|
| Mutable class defaults      | **Detect + Block**| Ruff RUF012 (no fix)|
| SequenceNotStr              | **Automated**     | mypy + useful-types |
| Tuple preference            | **Guidance only** | CLAUDE.md           |
| frozen=True preference      | **Guidance only** | CLAUDE.md           |

¹ B006's fix is classified as "unsafe" by ruff because it changes code behavior (`= []` → `= None`). We detect and report rather than auto-fix.

## Mutable Default Enforcement (Ruff)

### Configuration

```toml
# pyproject.toml
[tool.ruff.lint]
select = [
    "B006",   # mutable-argument-default
    "B039",   # mutable-contextvar-default
    "RUF008", # mutable-dataclass-default
    "RUF012", # mutable-class-default
]
```

### Hook Behavior

The PostToolUse hook runs Ruff in two passes:
1. **Fix pass**: `ruff check --fix` applies safe auto-fixes (formatting, imports)
2. **Check pass**: `ruff check` detects remaining issues (B006, RUF008, RUF012)

B006, RUF008, and RUF012 are detected and reported as errors requiring manual fix.

```python
# .claude-plugin/hooks/scripts/format_python.py

def format_file(file_path: str, config: PluginConfig) -> None:
    """Run formatters - Ruff handles B006, B039, RUF008, RUF012."""
    if config.level in ("strict", "moderate"):
        subprocess.run(
            ["uv", "run", "ruff", "check", "--fix", file_path],
            check=False,
            capture_output=True,
        )
    # ...
```

### Violations Caught

```python
# B006: Mutable argument default
def bad(items: list[str] = []) -> None:  # BLOCKED
    ...

# RUF008: Mutable default in dataclass
@dataclass
class Bad:
    items: list[str] = []  # BLOCKED
```

### Hook Output (PostToolUse)

```json
{
  "decision": "block",
  "reason": "Mutable default in example.py:\n  line 5: B006 Do not use mutable data structures for argument defaults"
}
```

**Note:** PostToolUse hooks cannot actually block (tool already executed). This output prompts Claude to fix the issue.

## SequenceNotStr Enforcement (mypy)

### Dependency

```toml
# pyproject.toml (consumer)
[project]
dependencies = [
    "useful-types>=0.2.1",
]
```

### Usage

```python
from useful_types import SequenceNotStr

def process_tags(tags: SequenceNotStr[str]) -> None:
    for tag in tags:
        print(tag)

process_tags("hello")  # mypy error: str is not SequenceNotStr
```

### Hook Behavior

The PostToolUse hook runs mypy in strict mode, which catches the type error:

```python
# .claude-plugin/hooks/scripts/format_python.py

def check_types(file_path: str, config: PluginConfig) -> list[str]:
    """Run mypy - catches SequenceNotStr violations."""
    if config.level != "strict":
        return []

    mypy_result = subprocess.run(
        ["uv", "run", "mypy", "--strict", file_path],
        check=False,
        capture_output=True,
        text=True,
    )

    if mypy_result.returncode != 0:
        errors = [line.strip() for line in mypy_result.stdout.strip().split("\n") if line.strip()]
        return errors

    return []
```

### Hook Output

```json
{
  "decision": "block",
  "reason": "Type errors in example.py:\nexample.py:10: error: Argument 1 to \"process_tags\" has incompatible type \"str\"; expected \"SequenceNotStr[str]\""
}
```

## Guidance-Only Patterns

These patterns cannot be linted but are documented in CLAUDE.md:

### CLAUDE.md Section

```markdown
## Immutability Patterns (ADR-013)

| Prefer | Over | Why |
|--------|------|-----|
| `tuple(items)` | `list.append()` loop | Immutable result |
| `@dataclass(frozen=True)` | `@dataclass` | Immutable objects |
| `NamedTuple` | `dataclass` (simple records) | Immutable by default |
| `frozenset()` | `set()` | Immutable sets |
| `Mapping[K, V]` | `dict[K, V]` (return type) | Read-only contract |
```

### SKILL.md Patterns

```markdown
## Building Collections

Prefer:
\`\`\`python
def get_names(users: list[User]) -> tuple[str, ...]:
    return tuple(u.name for u in users)
\`\`\`

Avoid:
\`\`\`python
def get_names(users: list[User]) -> list[str]:
    result = []
    for u in users:
        result.append(u.name)
    return result
\`\`\`
```

## Strictness Level Behavior

| Level | B006/B039/RUF008/RUF012 | mypy (SequenceNotStr) |
|-------|-------------------------|----------------------|
| strict | Detect + Block¹ | Block |
| moderate | Detect + Warn¹ | Skip |
| minimal | Skip | Skip |

¹ These rules detect violations but don't auto-fix (B006 fix is unsafe, RUF008/RUF012 have no fix).

## Testing

### Unit Tests

```python
# tests/test_format_python.py

def test_catches_mutable_default(tmp_path: Path) -> None:
    """Ruff catches mutable argument default."""
    file = tmp_path / "example.py"
    file.write_text("def bad(items: list = []): pass")

    result = subprocess.run(
        ["uv", "run", "ruff", "check", str(file)],
        capture_output=True,
        text=True,
    )

    assert "B006" in result.stdout


def test_mypy_catches_sequence_not_str(tmp_path: Path) -> None:
    """mypy catches str passed to SequenceNotStr."""
    file = tmp_path / "example.py"
    file.write_text('''
from useful_types import SequenceNotStr

def process(items: SequenceNotStr[str]) -> None:
    pass

process("hello")
''')

    result = subprocess.run(
        ["uv", "run", "mypy", "--strict", str(file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "SequenceNotStr" in result.stdout
```

### E2E Tests

```python
# tests/e2e/test_immutability.py

def test_blocks_mutable_default(e2e_project: Path) -> None:
    """Plugin catches mutable argument default."""
    result = write_file_via_claude(
        e2e_project,
        "src/example.py",
        "from __future__ import annotations\n\ndef bad(items: list[str] = []) -> None: pass",
    )

    assert "B006" in result.stdout or "mutable" in result.stdout.lower()
```

## Summary

| Pattern | Ruff Rule | mypy | Guidance |
|---------|-----------|------|----------|
| `def f(x=[])` | B006 | - | - |
| `ContextVar(default=[])` | B039 | - | - |
| `@dataclass` with `x: list = []` | RUF008 | - | - |
| Class with `x: list = []` | RUF012 | - | - |
| `Sequence[str]` footgun | - | useful-types | - |
| Tuple over list.append | - | - | CLAUDE.md |
| frozen=True preference | - | - | CLAUDE.md |
