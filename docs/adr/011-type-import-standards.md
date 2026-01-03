# ADR-011: Type Import Standards

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-29 |
| Deciders | TBD |
| Related | [ADR-010](010-python-version-compatibility.md), [ADR-008](008-linting-rule-strategy.md) |

## Context

Python's typing ecosystem spans multiple modules:
- `typing` - Original type hints module
- `collections.abc` - Abstract base classes for containers
- Built-in types - `list`, `dict`, `set`, `tuple` as generics (PEP 585)

Inconsistent imports create confusion, IDE/LSP issues, and version compatibility problems. PEP 585 (Python 3.9+) and PEP 604 (Python 3.10+) modernized the typing system.

## Decision

### 1. Import Source by Type Category

| Category | Import From | Examples |
|----------|-------------|----------|
| Protocols/ABCs | `collections.abc` | `Sequence`, `Mapping`, `Callable`, `Iterable`, `Iterator` |
| Container generics | Built-in | `list[str]`, `dict[str, int]`, `set[T]`, `tuple[int, ...]` |
| Special forms | `typing` | `Literal`, `TypeVar`, `Generic`, `Any`, `cast` |
| Union syntax | Built-in | `X \| Y`, `X \| None` |
| Type aliases | `typing` (3.10+) | `TypeAlias` |
| Version compat | `typing_extensions` | See [ADR-010](010-python-version-compatibility.md) |

### 2. Deprecated Imports (Avoid)

| Deprecated | Use Instead | Ruff Rule |
|------------|-------------|-----------|
| `typing.List` | `list` | UP006 |
| `typing.Dict` | `dict` | UP006 |
| `typing.Set` | `set` | UP006 |
| `typing.Tuple` | `tuple` | UP006 |
| `typing.Union[X, Y]` | `X \| Y` | UP007 |
| `typing.Optional[X]` | `X \| None` | UP007 |
| `typing.Callable` | `collections.abc.Callable` | UP035 |
| `typing.Sequence` | `collections.abc.Sequence` | UP035 |

### 3. Correct Import Patterns

```python
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, TypeVar

if TYPE_CHECKING:
    from collections.abc import Generator
```

### 4. TYPE_CHECKING Block Usage

Use `TYPE_CHECKING` for:
- Import-only types (not used at runtime)
- Circular import avoidance
- Heavy imports used only in annotations

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from heavy_module import ExpensiveClass
    from .models import SomeModel

def process(item: ExpensiveClass) -> SomeModel:
    ...
```

### 5. Ruff Enforcement Rules

| Rule | Purpose | Action |
|------|---------|--------|
| UP006 | Use builtin generics | `list` not `typing.List` |
| UP007 | Use `X \| Y` syntax | Not `Union[X, Y]` |
| UP035 | Deprecated typing imports | `collections.abc.Callable` |
| TCH001 | Move typing-only imports to TYPE_CHECKING | Reduce runtime imports |
| TCH002 | Third-party typing imports in TYPE_CHECKING | Reduce load time |
| TCH003 | Stdlib typing imports in TYPE_CHECKING | Reduce load time |
| TCH004 | Remove unused TYPE_CHECKING imports | Clean up |

### 6. Configuration

```toml
[tool.ruff.lint]
select = [
    "UP",   # pyupgrade (UP006, UP007, UP035)
    "TCH",  # flake8-type-checking
]

[tool.ruff.lint.flake8-type-checking]
strict = true  # Aggressive TYPE_CHECKING movement
```

### 7. LSP Surfacing Best Practices

For optimal IDE/LSP experience:

| Practice | Reason |
|----------|--------|
| Import from `collections.abc` for protocols | Consistent cross-version behavior |
| Avoid type re-exports in `__init__.py` | Cleaner import paths in tooltips |
| Use explicit imports over `*` | Better autocomplete |
| Define types close to usage | Easier navigation |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| `typing` module only | Deprecated for generics; UP006/UP035 violations |
| No enforcement | Inconsistent codebase, IDE issues |
| Strict TCH everywhere | May break runtime type introspection |

## Consequences

### Positive

- Consistent import patterns across codebase
- Modern Python idioms (PEP 585, 604)
- Faster startup (TYPE_CHECKING blocks)
- Better IDE/LSP experience
- Automatic enforcement via Ruff

### Negative

- Learning curve for deprecated patterns
- May require codebase migration
- TYPE_CHECKING can complicate debugging

### Risks

| Risk | Mitigation |
|------|------------|
| Runtime type access breaks | Use `get_type_hints()` with include_extras |
| Circular import complexity | Document patterns, use TYPE_CHECKING |
| Over-aggressive TCH rules | Configure exceptions as needed |

## References

- [PEP 585 - Type Hinting Generics In Standard Collections](https://peps.python.org/pep-0585/)
- [PEP 604 - Allow writing union types as X \| Y](https://peps.python.org/pep-0604/)
- [Ruff UP rules](https://docs.astral.sh/ruff/rules/#pyupgrade-up)
- [Ruff TCH rules](https://docs.astral.sh/ruff/rules/#flake8-type-checking-tch)

## Approval Checklist

- [ ] Ruff UP and TCH rules enabled in pyproject.toml
- [ ] Existing codebase migrated to new patterns
- [ ] CLAUDE.md updated with import guidance
- [ ] No runtime type introspection breakage verified
