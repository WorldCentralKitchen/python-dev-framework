# ADR-010: Python Version Compatibility

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-29 |
| Deciders | TBD |
| Related | [ADR-001](001-python-dev-framework-architecture.md), [ADR-008](008-linting-rule-strategy.md), [ADR-011](011-type-import-standards.md) |

## Context

The framework currently targets Python 3.12+ exclusively. Consumer projects may need to support older Python versions due to **library compatibility** — some packages consumers depend on may not yet support the latest Python versions.

Python's typing ecosystem has evolved significantly across versions, requiring version-specific guidance for type hints and imports.

## Decision

### 1. Supported Version Matrix

| Version | Support Level | typing_extensions | Notes |
|---------|---------------|-------------------|-------|
| 3.9 | Full | Required | Minimum supported |
| 3.10 | Full | Recommended | Union syntax native |
| 3.11 | Full | Optional | Exception groups, Self |
| 3.12 | Full (default) | Not needed | Type parameter syntax |
| 3.13 | Full | Not needed | Latest stable |

### 2. Required Practices

All modules MUST include:

```python
from __future__ import annotations
```

This enables:
- PEP 563 postponed evaluation of annotations
- Forward references without quotes
- Consistent behavior across versions
- Reduced runtime overhead

### 3. typing_extensions Usage

Use `typing_extensions` for features not in target version's stdlib:

| Feature | stdlib Version | typing_extensions |
|---------|----------------|-------------------|
| `Self` | 3.11+ | 3.9-3.10 |
| `TypeAlias` | 3.10+ | 3.9 |
| `override` | 3.12+ | 3.9-3.11 |
| `TypeGuard` | 3.10+ | 3.9 |
| `ParamSpec` | 3.10+ | 3.9 |
| `Concatenate` | 3.10+ | 3.9 |

Import pattern:

```python
from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
```

### 4. Version-Specific Syntax

| Feature | Python 3.9 | Python 3.10+ |
|---------|------------|--------------|
| Union types | `Union[X, Y]` or `X \| Y` (with future) | `X \| Y` |
| Optional | `Optional[X]` or `X \| None` | `X \| None` |
| Type guards | `typing_extensions.TypeGuard` | `typing.TypeGuard` |
| Match statements | Not available | Allowed |
| Generic builtins | `list[str]` (with future) | `list[str]` |
| TypeAlias | `typing_extensions.TypeAlias` | `typing.TypeAlias` |

### 5. Configuration

Consumer pyproject.toml:

```toml
[project]
requires-python = ">=3.9"  # Or project-specific minimum

[project.optional-dependencies]
dev = [
    "typing-extensions>=4.0",  # Required for 3.9-3.10
]

[tool.ruff]
target-version = "py39"  # Match requires-python

[tool.mypy]
python_version = "3.9"  # Match requires-python
```

### 6. Framework Default

The framework itself defaults to Python 3.12+ for development but generates configurations supporting 3.9+ for consumers.

## Alternatives Considered

| Alternative                          | Rejected Because                       |
| ------------------------------------ | -------------------------------------- |
| 3.12+ only                           | Excludes projects with library constraints |
| 3.8 support                          | EOL, typing limitations too severe     |
| No typing_extensions                 | Forces version-specific code paths     |
| Runtime version detection everywhere | Complex, error-prone                   |

## Consequences

### Positive

- Consumers can use libraries that don't yet support latest Python
- Single codebase supports multiple Python versions
- typing_extensions provides forward compatibility

### Negative

- Additional dependency for older versions
- Documentation must cover version differences
- Testing matrix expands

### Risks

| Risk | Mitigation |
|------|------------|
| Version-specific bugs | CI matrix tests all supported versions |
| typing_extensions drift | Pin minimum version, monitor releases |
| `__future__` removal | PEP 563 behavior stable; annotations postponement permanent |

## References

- [PEP 563 - Postponed Evaluation of Annotations](https://peps.python.org/pep-0563/)
- [PEP 585 - Type Hinting Generics In Standard Collections](https://peps.python.org/pep-0585/)
- [PEP 604 - Union Operators](https://peps.python.org/pep-0604/)
- [typing_extensions documentation](https://typing-extensions.readthedocs.io/)

## Approval Checklist

- [ ] CI matrix includes Python 3.9, 3.10, 3.11, 3.12, 3.13
- [ ] typing_extensions added to consumer template
- [ ] Version-specific syntax documented in CLAUDE.md
- [ ] Ruff/mypy target-version guidance documented
