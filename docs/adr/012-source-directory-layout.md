# ADR-012: Source Directory Layout

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-29 |
| Deciders | TBD |
| Related | [ADR-001](001-python-dev-framework-architecture.md), [ADR-004](004-prescribed-dependencies.md) |

## Context

Consumer projects need consistent conventions for organizing:
- Type definitions (aliases, protocols, type vars)
- Data models (dataclasses, attrs, Pydantic)
- Internal utilities vs public APIs
- Module naming for visibility

Without conventions, codebases become inconsistent, making navigation and maintenance difficult.

## Decision

### 1. Standard Directory Structure

```
src/
└── package_name/
    ├── __init__.py           # Package exports
    ├── py.typed               # PEP 561 marker
    │
    ├── types/                 # Type definitions
    │   ├── __init__.py        # Public type exports
    │   ├── _internal.py       # Internal type aliases (private)
    │   ├── protocols.py       # Protocol definitions
    │   └── aliases.py         # Public TypeAliases
    │
    ├── models/                # Data containers
    │   ├── __init__.py        # Model exports
    │   ├── domain.py          # Domain dataclasses/attrs
    │   └── api.py             # Pydantic models (API boundaries only)
    │
    ├── _internal/             # Private implementation
    │   ├── __init__.py
    │   └── utils.py           # Internal utilities
    │
    └── core/                  # Public modules
        ├── __init__.py
        └── service.py
```

### 2. Naming Conventions

| Pattern | Visibility | Usage |
|---------|------------|-------|
| `types/` | Public directory | Type definitions |
| `_internal.py` | Private module | Internal types, not exported |
| `models/` | Public directory | Data containers |
| `_internal/` | Private directory | Implementation details |
| `_utils.py` | Private module | Helper functions |
| Leading underscore | Private | Never import from outside package |

### 3. types/ Directory Pattern

```python
# types/_internal.py (PRIVATE - do not import externally)
from __future__ import annotations

from typing import TypeAlias

# Internal type aliases
_PathLike: TypeAlias = str | os.PathLike[str]
_JsonValue: TypeAlias = str | int | float | bool | None | list | dict


# types/protocols.py (PUBLIC)
from __future__ import annotations

from typing import Protocol, runtime_checkable

@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


# types/aliases.py (PUBLIC)
from __future__ import annotations

from typing import TypeAlias

Result: TypeAlias = tuple[bool, str | None]
ErrorCode: TypeAlias = int


# types/__init__.py (PUBLIC EXPORTS)
from __future__ import annotations

from .aliases import ErrorCode, Result
from .protocols import Serializable

__all__ = ["ErrorCode", "Result", "Serializable"]
# Note: _internal types are NOT exported
```

### 4. models/ Directory Pattern

```python
# models/domain.py (DOMAIN LOGIC - dataclasses/attrs)
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)  # Prefer frozen for immutability
class User:
    id: str
    email: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Order:
    id: str
    user_id: str
    items: list[str] = field(default_factory=list)


# models/api.py (API BOUNDARIES ONLY - Pydantic)
from __future__ import annotations

from pydantic import BaseModel, EmailStr


class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str


class UserResponse(BaseModel):
    id: str
    email: str

    class Config:
        from_attributes = True  # Enable ORM mode


# models/__init__.py
from .api import CreateUserRequest, UserResponse
from .domain import Order, User

__all__ = ["CreateUserRequest", "Order", "User", "UserResponse"]
```

### 5. Pydantic Boundary Rule

| Location | Model Type | Rationale |
|----------|------------|-----------|
| `models/api.py` | Pydantic | External input/output validation |
| `models/domain.py` | dataclass/attrs | Internal logic, no runtime validation overhead |
| Function internals | dataclass | Simple data passing |

Pydantic ONLY at boundaries:
- REST request/response bodies
- CLI argument parsing
- Configuration file loading
- Message queue payloads
- External API responses

### 6. _internal/ Directory Pattern

```python
# _internal/utils.py
from __future__ import annotations

def _normalize_path(path: str) -> str:
    """Internal helper - not part of public API."""
    ...

# _internal/__init__.py
# Empty or minimal - consumers should never import from here
```

### 7. Import Rules

| Rule | Allowed | Forbidden |
|------|---------|-----------|
| Public → Public | Yes | - |
| Public → _internal | No | Cross-package _internal imports |
| _internal → Public | Yes | - |
| _internal → _internal (same pkg) | Yes | - |
| External → _internal | No | Any external _internal imports |

Ruff SLF001 enforces private member access restrictions.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Flat structure | Poor organization at scale |
| `typing.py` single file | Grows unwieldy, mixes concerns |
| No models/ separation | Unclear Pydantic vs dataclass usage |
| `utils/` public directory | Encourages dumping ground |

## Consequences

### Positive

- Clear separation of public vs private
- Consistent navigation across projects
- Pydantic confined to boundaries
- Type definitions easily located
- IDE/LSP import suggestions improved

### Negative

- More directories to create
- Boilerplate `__init__.py` files
- Learning curve for conventions

### Risks

| Risk | Mitigation |
|------|------------|
| Over-engineering small projects | Adopt progressively; start with flat |
| Circular imports | types/ has no dependencies; models/ imports types/ |
| _internal leakage | Ruff SLF001 enforcement |

## Approval Checklist

- [ ] Template project structure created
- [ ] CLAUDE.md updated with layout conventions
- [ ] Example consumer project validates structure
- [ ] Ruff SLF001 enabled for private access
