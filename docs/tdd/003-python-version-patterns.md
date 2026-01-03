# TDD-003: Python Version Compatibility Implementation

| Field | Value |
|-------|-------|
| Version | 0.2.0 |
| Date | 2025-12-29 |
| Related ADRs | [ADR-010](../adr/010-python-version-compatibility.md) |

## Overview

How the plugin detects Python version and enforces version-appropriate patterns.

## Version Detection

### Detection Flow

```
┌─────────────────────────────────────────────────────────────┐
│ PostToolUse Hook (Write/Edit .py file)                      │
├─────────────────────────────────────────────────────────────┤
│ 1. Read pyproject.toml from project root                    │
│ 2. Extract target version from (in priority order):         │
│    a. tool.ruff.target-version (e.g., "py39")              │
│    b. project.requires-python (e.g., ">=3.9")              │
│    c. Default to py312 if not specified                     │
│ 3. Pass --target-version to ruff check                      │
│ 4. Pass python_version to mypy                              │
└─────────────────────────────────────────────────────────────┘
```

### Implementation: config.py Updates

```python
# .claude-plugin/hooks/scripts/config.py
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PluginConfig:
    level: StrictnessLevel = "strict"
    target_python: str = "py312"  # NEW: Detected Python version
    # ... existing fields


def detect_python_version(project_root: Path) -> str:
    """Detect target Python version from pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return "py312"  # Default

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    # Priority 1: Ruff target-version
    ruff_target = data.get("tool", {}).get("ruff", {}).get("target-version")
    if ruff_target:
        return ruff_target  # e.g., "py39"

    # Priority 2: project.requires-python
    requires = data.get("project", {}).get("requires-python", "")
    match = re.search(r">=?\s*3\.(\d+)", requires)
    if match:
        minor = match.group(1)
        return f"py3{minor}"

    return "py312"


def load_config(project_root: Path | None = None) -> PluginConfig:
    """Load plugin config with Python version detection."""
    # ... existing settings.json loading ...

    if project_root:
        target_python = detect_python_version(project_root)
    else:
        target_python = "py312"

    return PluginConfig(
        level=level,
        target_python=target_python,
        # ...
    )
```

### Implementation: format_python.py Updates

```python
# .claude-plugin/hooks/scripts/format_python.py

def format_file(file_path: Path, config: PluginConfig) -> tuple[bool, str]:
    """Format file with version-aware rules."""

    # Pass target version to ruff
    ruff_cmd = [
        "ruff", "check", "--fix",
        "--target-version", config.target_python,  # NEW
        str(file_path),
    ]

    # ... run ruff ...

    return success, output


def check_types(file_path: Path, config: PluginConfig) -> tuple[bool, str]:
    """Type check with version-aware settings."""

    # Extract version number (py39 -> 3.9)
    version = config.target_python.replace("py3", "3.")

    mypy_cmd = [
        "mypy",
        "--python-version", version,  # NEW
        str(file_path),
    ]

    # ... run mypy ...
```

## Enforcement: `__future__` Annotations

### Hook Check

The PostToolUse hook verifies `from __future__ import annotations` is present:

```python
# .claude-plugin/hooks/scripts/format_python.py
import json
from pathlib import Path

def check_future_annotations(file_path: Path) -> tuple[bool, str | None]:
    """Check for required __future__ import."""
    content = file_path.read_text()

    # Skip if file is empty or only comments
    lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
    if not lines:
        return True, None

    # Check for __future__ import in first non-comment lines
    if "from __future__ import annotations" not in content:
        return False, "Missing 'from __future__ import annotations' at top of file"

    return True, None


def main() -> None:
    # ... existing hook logic (read stdin context, load config) ...

    # Check __future__ annotations (strict mode only)
    if config.level == "strict":
        ok, error = check_future_annotations(Path(file_path))
        if not ok:
            # PostToolUse can't block, but this prompts Claude to fix
            print(json.dumps({
                "decision": "block",
                "reason": error,
            }))
            return
    # No output needed for success
```

### Ruff Rule Enforcement

Enable Ruff rule to catch missing `__future__` imports:

```toml
# pyproject.toml (consumer)
[tool.ruff.lint]
select = [
    "FA",  # flake8-future-annotations
]
```

The plugin's Ruff invocation includes this rule when target version < py310:

```python
def get_ruff_rules(target_python: str) -> list[str]:
    """Get Ruff rules based on target Python version."""
    base_rules = ["E", "W", "F", "I", "B", ...]

    # Add FA rules for older Python to catch __future__ issues
    if target_python in ("py39", "py310"):
        base_rules.append("FA")

    return base_rules
```

## Version-Specific Rule Adjustments

### Ruff Rules by Version

```python
def get_version_specific_ignores(target_python: str) -> list[str]:
    """Get rules to ignore based on Python version."""
    ignores = []

    if target_python == "py39":
        # Python 3.9 doesn't have match statements
        ignores.append("UP036")  # pyupgrade: use match

    return ignores
```

## Hook Output Protocol

PostToolUse hooks output JSON to stdout. Since PostToolUse runs after the tool executes, it cannot actually block—the "block" decision prompts Claude to address the issue.

### Output Helper Function

```python
import json

def output_block(reason: str) -> None:
    """Output block response to prompt Claude about issues."""
    print(json.dumps({
        "decision": "block",
        "reason": reason,
    }))
```

### Example Outputs

**Missing `__future__` annotations:**
```json
{"decision": "block", "reason": "Missing 'from __future__ import annotations' at top of file"}
```

**Version-specific type issue:**
```json
{"decision": "block", "reason": "Python 3.9 target detected. Use typing_extensions.Self instead of typing.Self"}
```

**Success:** No output needed (or `sys.exit(0)`)

## Consumer Configuration

### pyproject.toml Template

```toml
[project]
requires-python = ">=3.9"

[tool.ruff]
target-version = "py39"  # Must match requires-python

[tool.mypy]
python_version = "3.9"   # Must match requires-python

[project.optional-dependencies]
dev = [
    "typing-extensions>=4.0",  # Required for 3.9-3.10
]
```

## Testing

### Unit Tests

```python
# tests/test_config.py

def test_detect_python_version_from_ruff(tmp_path: Path) -> None:
    """Detect version from ruff config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.ruff]\ntarget-version = "py39"')

    assert detect_python_version(tmp_path) == "py39"


def test_detect_python_version_from_requires(tmp_path: Path) -> None:
    """Detect version from requires-python."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = ">=3.10"')

    assert detect_python_version(tmp_path) == "py310"


def test_detect_python_version_default(tmp_path: Path) -> None:
    """Default to py312 when no config."""
    assert detect_python_version(tmp_path) == "py312"
```

### E2E Tests

```python
# tests/e2e/test_version_hook.py

def test_blocks_missing_future_annotations(e2e_project: Path) -> None:
    """Hook blocks file without __future__ import."""
    result = write_file_via_claude(
        e2e_project,
        "src/example.py",
        "def foo(x: str | None) -> None: pass",
    )

    assert "block" in result.stdout
    assert "__future__" in result.stdout


def test_allows_with_future_annotations(e2e_project: Path) -> None:
    """Hook allows file with __future__ import."""
    result = write_file_via_claude(
        e2e_project,
        "src/example.py",
        "from __future__ import annotations\n\ndef foo(x: str | None) -> None: pass",
    )

    assert "block" not in result.stdout
```

## Reference: typing_extensions Features

| Feature | stdlib Version | Import for 3.9 |
|---------|----------------|----------------|
| `Self` | 3.11 | `from typing_extensions import Self` |
| `TypeAlias` | 3.10 | `from typing_extensions import TypeAlias` |
| `override` | 3.12 | `from typing_extensions import override` |
| `TypeGuard` | 3.10 | `from typing_extensions import TypeGuard` |
