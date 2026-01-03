# TDD-004: Type Import Enforcement Implementation

| Field | Value |
|-------|-------|
| Version | 0.2.0 |
| Date | 2025-12-29 |
| Related ADRs | [ADR-011](../adr/011-type-import-standards.md) |

## Overview

How the plugin enforces type import standards via Ruff rules and hooks.

## Enforcement Strategy

Type import standards are enforced through **Ruff rules only**—no custom hook logic needed. The plugin ensures the correct Ruff rules are enabled and executed.

```
┌─────────────────────────────────────────────────────────────┐
│ Enforcement: Ruff Rules (no custom hook logic)              │
├─────────────────────────────────────────────────────────────┤
│ UP006  - Use list instead of typing.List                    │
│ UP007  - Use X | Y instead of Union[X, Y]                  │
│ UP035  - Deprecated typing imports (Callable, etc.)         │
│ TCH001 - Move app imports to TYPE_CHECKING                  │
│ TCH002 - Move third-party imports to TYPE_CHECKING          │
│ TCH003 - Move stdlib imports to TYPE_CHECKING               │
│ TCH004 - Remove unused TYPE_CHECKING imports                │
└─────────────────────────────────────────────────────────────┘
```

## Implementation: Ruff Configuration

### pyproject.toml (Plugin Default)

```toml
[tool.ruff.lint]
select = [
    # ... existing rules ...
    "UP",   # pyupgrade - includes UP006, UP007, UP035
    "TCH",  # flake8-type-checking
]

[tool.ruff.lint.flake8-type-checking]
strict = true  # Aggressively move imports to TYPE_CHECKING
```

### format_python.py Hook

The existing hook runs Ruff with `--fix`, which auto-corrects most violations:

```python
# .claude-plugin/hooks/scripts/format_python.py

def format_file(file_path: Path, config: PluginConfig) -> tuple[bool, str]:
    """Format file - Ruff handles type import rules via UP and TCH."""

    ruff_cmd = [
        "ruff", "check",
        "--fix",  # Auto-fix UP006, UP007, UP035
        "--target-version", config.target_python,
        str(file_path),
    ]

    result = subprocess.run(ruff_cmd, capture_output=True, text=True)

    # Ruff auto-fixes:
    # - typing.List -> list
    # - Union[X, Y] -> X | Y
    # - typing.Callable -> collections.abc.Callable

    return result.returncode == 0, result.stdout + result.stderr
```

## Auto-Fix Behavior

### What Ruff Fixes Automatically

| Rule | Before | After |
|------|--------|-------|
| UP006 | `List[str]` | `list[str]` |
| UP006 | `Dict[str, int]` | `dict[str, int]` |
| UP007 | `Union[str, int]` | `str \| int` |
| UP007 | `Optional[str]` | `str \| None` |
| UP035 | `from typing import Callable` | `from collections.abc import Callable` |

### What Requires Manual Fix

| Rule | Issue | Why Not Auto-Fixed |
|------|-------|-------------------|
| TCH001-003 | Move to TYPE_CHECKING | May affect runtime behavior |
| UP035 | Some deprecated imports | Complex refactoring needed |

## Hook Output Protocol

PostToolUse hooks output JSON to stdout. Since PostToolUse runs after the tool executes, it cannot actually block—the "block" decision prompts Claude to address the issue.

### Successful Auto-Fix

No output needed—Ruff auto-fixes issues and the hook exits silently (`sys.exit(0)`).

### Remaining Issues (Strict Mode)

When unfixable issues remain, output prompts Claude to address them:

```json
{"decision": "block", "reason": "Type import issues in example.py:\n- line 5: TCH001 Move import to TYPE_CHECKING block"}
```

### Output Helper

```python
import json

def output_block(reason: str) -> None:
    """Output block response to prompt Claude about issues."""
    print(json.dumps({"decision": "block", "reason": reason}))
```

## Strictness Level Behavior

| Level | UP Rules | TCH Rules |
|-------|----------|-----------|
| strict | Fix + Block unfixed | Fix + Block unfixed |
| moderate | Fix + Warn unfixed | Disabled |
| minimal | Disabled | Disabled |

### Implementation

```python
def get_ruff_select_rules(level: StrictnessLevel) -> list[str]:
    """Get Ruff rules based on strictness level."""
    if level == "strict":
        return ["E", "W", "F", "I", "B", "UP", "TCH", ...]
    elif level == "moderate":
        return ["E", "W", "F", "I", "B", "UP", ...]  # No TCH
    else:  # minimal
        return ["E", "W", "F"]  # Basic only
```

## LSP Integration

The Ruff LSP server provides real-time diagnostics for type import issues:

```json
// .claude-plugin/.lsp.json
{
  "servers": [
    {
      "command": "ruff",
      "args": ["server"],
      "languages": [{"name": "python", "extensions": [".py", ".pyi"]}]
    }
  ]
}
```

LSP shows violations as you type, before the PostToolUse hook runs.

## Testing

### Unit Tests

```python
# tests/test_format_python.py

def test_fixes_typing_list(tmp_path: Path) -> None:
    """Ruff fixes typing.List to list."""
    file = tmp_path / "example.py"
    file.write_text("from typing import List\nx: List[str] = []")

    config = PluginConfig(level="strict")
    success, _ = format_file(file, config)

    assert success
    assert "list[str]" in file.read_text()
    assert "List" not in file.read_text()


def test_fixes_union_syntax(tmp_path: Path) -> None:
    """Ruff fixes Union to | syntax."""
    file = tmp_path / "example.py"
    file.write_text(
        "from __future__ import annotations\n"
        "from typing import Union\n"
        "x: Union[str, int] = 'a'"
    )

    config = PluginConfig(level="strict")
    success, _ = format_file(file, config)

    assert success
    content = file.read_text()
    assert "str | int" in content
    assert "Union" not in content
```

### E2E Tests

```python
# tests/e2e/test_type_imports.py

def test_fixes_deprecated_imports(e2e_project: Path) -> None:
    """Plugin auto-fixes deprecated typing imports."""
    result = write_file_via_claude(
        e2e_project,
        "src/example.py",
        "from typing import List, Dict\nx: List[Dict[str, int]] = []",
    )

    # Check file was fixed
    content = (e2e_project / "src/example.py").read_text()
    assert "list[dict[str, int]]" in content
```

## Reference: Correct Import Patterns

| Type | Correct Import |
|------|----------------|
| `Callable` | `from collections.abc import Callable` |
| `Sequence` | `from collections.abc import Sequence` |
| `Mapping` | `from collections.abc import Mapping` |
| `Iterable` | `from collections.abc import Iterable` |
| `list[T]` | Built-in (no import needed) |
| `dict[K, V]` | Built-in (no import needed) |
| `X \| Y` | Built-in (with `__future__` on 3.9) |
| `Any` | `from typing import Any` |
| `TypeVar` | `from typing import TypeVar` |
