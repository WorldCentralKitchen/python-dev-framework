# TDD-005: Directory Layout Implementation

| Field | Value |
|-------|-------|
| Version | 0.2.0 |
| Date | 2025-12-29 |
| Related ADRs | [ADR-012](../adr/012-source-directory-layout.md) |

## Overview

How the plugin enforces directory layout conventions and private access patterns.

## Enforcement Strategy

| Aspect | Enforcement | Mechanism |
|--------|-------------|-----------|
| Private attribute access (`obj._attr`) | **Automated** | Ruff SLF001 |
| Private module naming (`_internal/`) | **Guidance only** | CLAUDE.md |
| Directory structure | **Guidance only** | CLAUDE.md, SKILL.md |
| Pydantic at boundaries | **Guidance only** | CLAUDE.md, code review |

**Note:** Ruff SLF001 catches private **attribute/method access** on objects (e.g., `obj._secret`),
but does NOT catch imports from `_internal/` modules. The `_internal/` naming is convention-based guidance.

## Private Access Enforcement (SLF001)

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff.lint]
select = [
    "SLF",  # flake8-self (private member access)
]

[tool.ruff.lint.per-file-ignores]
# Allow private access within package internals
"src/*/_internal/*.py" = ["SLF001"]
"tests/**/*.py" = ["SLF001"]
```

### Hook Behavior

The PostToolUse hook runs Ruff which catches SLF001 violations:

```python
# .claude-plugin/hooks/scripts/format_python.py

# SLF001 is included in standard ruff check
# No custom hook logic needed - Ruff handles it
```

### Example Violations

```python
# src/mypackage/service.py

# SLF001 VIOLATION: Accessing private attribute on object
config = Config()
secret = config._secret_key  # Blocked by SLF001

# SLF001 VIOLATION: Calling private method on object
result = service._internal_method()  # Blocked by SLF001

# NOT caught by SLF001 (convention-based guidance only):
from mypackage._internal.utils import _generate_id
from mypackage.types._internal import _PathLike
```

### Hook Output

PostToolUse hooks output JSON to stdout. Since PostToolUse runs after the tool executes, it cannot actually block—the "block" decision prompts Claude to address the issue.

```json
{"decision": "block", "reason": "SLF001: Private member access: mypackage._internal.utils._generate_id"}
```

**Success:** No output needed (Ruff auto-fixes or no violations found).

## Directory Structure Guidance

### CLAUDE.md Section

The plugin's CLAUDE.md documents expected structure:

```markdown
## Directory Layout (ADR-012)

| Directory | Contents |
|-----------|----------|
| `types/` | Type definitions; `_internal.py` for private |
| `models/` | Dataclasses (domain), Pydantic (API only in `api.py`) |
| `_internal/` | Private utilities; never import externally |
```

### SKILL.md Patterns

The plugin's SKILL.md provides scaffolding patterns Claude can use:

```markdown
## Creating New Package Structure

When creating a new Python package, use this structure:

\`\`\`
src/package_name/
├── __init__.py
├── py.typed
├── types/
│   ├── __init__.py
│   └── _internal.py
├── models/
│   ├── __init__.py
│   ├── domain.py
│   └── api.py
└── _internal/
    └── utils.py
\`\`\`
```

## SessionStart Hook (Optional Enhancement)

A SessionStart hook could warn about missing directories:

```python
# .claude-plugin/hooks/scripts/check_structure.py
from __future__ import annotations

import json
from pathlib import Path


def check_project_structure() -> dict:
    """Check for recommended directories."""
    project_root = Path.cwd()
    src = project_root / "src"

    if not src.exists():
        return {"warnings": []}  # Not a src-layout project

    # Find package directories
    packages = [d for d in src.iterdir() if d.is_dir() and not d.name.startswith("_")]

    warnings = []
    for pkg in packages:
        if not (pkg / "types").exists():
            warnings.append(f"Consider adding {pkg.name}/types/ for type definitions")
        if not (pkg / "models").exists():
            warnings.append(f"Consider adding {pkg.name}/models/ for data models")

    return {"warnings": warnings}


if __name__ == "__main__":
    result = check_project_structure()
    if result["warnings"]:
        print(json.dumps({
            "message": "Directory structure suggestions:\n" + "\n".join(result["warnings"])
        }))
```

### hooks.json Configuration

```json
{
  "hooks": [
    {
      "type": "SessionStart",
      "script": "scripts/check_structure.py"
    }
  ]
}
```

**Status:** Optional enhancement—not in initial implementation.

## File Templates

### types/__init__.py Template

```python
"""Public type definitions."""

from __future__ import annotations

from .aliases import ErrorCode, Result
from .protocols import Serializable

__all__ = ["ErrorCode", "Result", "Serializable"]
```

### types/_internal.py Template

```python
"""Internal type aliases - do not import from outside package."""

from __future__ import annotations

from typing import TypeAlias

# Internal-only types (will trigger SLF001 if imported externally)
_PathLike: TypeAlias = str | os.PathLike[str]
_JsonValue: TypeAlias = str | int | float | bool | None | list | dict
```

### models/domain.py Template

```python
"""Domain models using dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: str
    email: str
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### models/api.py Template

```python
"""API boundary models using Pydantic."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str


class UserResponse(BaseModel):
    id: str
    email: str

    model_config = {"from_attributes": True}
```

## Testing

### Unit Tests

```python
# tests/test_private_access.py

def test_slf001_blocks_private_import(tmp_path: Path) -> None:
    """SLF001 catches private module imports."""
    file = tmp_path / "example.py"
    file.write_text("from mypackage._internal.utils import helper")

    result = subprocess.run(
        ["ruff", "check", str(file)],
        capture_output=True,
        text=True,
    )

    assert "SLF001" in result.stdout
```

### E2E Tests

```python
# tests/e2e/test_private_access.py

def test_blocks_private_import(e2e_project: Path) -> None:
    """Plugin blocks private member access."""
    # Create _internal module
    internal = e2e_project / "src" / "pkg" / "_internal"
    internal.mkdir(parents=True)
    (internal / "__init__.py").write_text("")
    (internal / "utils.py").write_text("def _helper(): pass")

    # Try to import from _internal in public module
    result = write_file_via_claude(
        e2e_project,
        "src/pkg/service.py",
        "from pkg._internal.utils import _helper",
    )

    assert "SLF001" in result.stdout or "block" in result.stdout
```

## Summary

| Convention | Enforcement |
|------------|-------------|
| `obj._private_attr` access | Ruff SLF001 (automated) |
| `obj._private_method()` calls | Ruff SLF001 (automated) |
| `_internal/` module naming | CLAUDE.md guidance |
| `types/` directory | CLAUDE.md guidance |
| `models/` directory | CLAUDE.md guidance |
| Pydantic in `api.py` only | CLAUDE.md guidance |
