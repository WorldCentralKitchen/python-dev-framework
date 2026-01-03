# ADR-013: Immutability and Safety Patterns

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-29 |
| Deciders | TBD |
| Related | [ADR-004](004-prescribed-dependencies.md), [ADR-008](008-linting-rule-strategy.md), [ADR-012](012-source-directory-layout.md) |

## Context

Mutable state is a common source of bugs in Python:
- Mutable default arguments
- Accidental list mutation
- `str` as `Sequence[str]` (footgun)
- Leaked mutable references

Enforcing immutability patterns reduces bugs and improves code reasoning.

## Decision

### 1. Ruff Enforcement (Automated)

| Pattern | Rule | Action |
|---------|------|--------|
| Mutable argument defaults | B006 | Block |
| Mutable contextvar defaults | B039 | Block |
| Mutable dataclass defaults | RUF008 | Block |
| Mutable class defaults | RUF012 | Block |

```toml
[tool.ruff.lint]
select = [
    "B006",   # mutable-argument-default
    "B039",   # mutable-contextvar-default
    "RUF008", # mutable-dataclass-default
    "RUF012", # mutable-class-default
]
```

Examples caught:

```python
# B006: BLOCKED
def process(items: list[str] = []) -> None:  # Mutable default
    ...

# Correct
def process(items: list[str] | None = None) -> None:
    items = items or []
    ...

# RUF008: BLOCKED
@dataclass
class Config:
    tags: list[str] = []  # Mutable dataclass default

# Correct
@dataclass
class Config:
    tags: list[str] = field(default_factory=list)
```

### 2. SequenceNotStr Protocol

`Sequence[str]` is a common footgun: a single `str` satisfies `Sequence[str]`.

```python
# BUG: Passes type check but wrong behavior
def process_items(items: Sequence[str]) -> None:
    for item in items:
        print(item)

process_items("hello")  # Iterates 'h', 'e', 'l', 'l', 'o'
```

**Solution:** Use `SequenceNotStr` from `useful-types`:

```toml
[project]
dependencies = [
    "useful-types>=0.2.1",
]
```

```python
from useful_types import SequenceNotStr

def process_items(items: SequenceNotStr[str]) -> None:
    for item in items:
        print(item)

process_items("hello")  # Type error!
process_items(["hello", "world"])  # Correct
```

### 3. Collection Building Patterns

| Prefer | Avoid | Rationale |
|--------|-------|-----------|
| `tuple(generator())` | `list.append()` loop | Immutable result |
| `items = ("a", "b", "c")` | `items = []; items.append()` | Fixed known items |
| Generator expression | List comprehension (when possible) | Lazy evaluation |
| `frozenset()` | `set()` | Immutable sets |

Examples:

```python
# PREFER: Tuple from generator
def get_file_names(paths: Iterable[Path]) -> tuple[str, ...]:
    return tuple(p.name for p in paths)

# AVOID: List append loop
def get_file_names(paths: Iterable[Path]) -> list[str]:
    result = []
    for p in paths:
        result.append(p.name)
    return result

# PREFER: Fixed tuple
VALID_EXTENSIONS = (".py", ".pyi", ".pyx")

# AVOID: Mutable list for constants
VALID_EXTENSIONS = [".py", ".pyi", ".pyx"]
```

### 4. Return Type Patterns

| Return Type | Use When |
|-------------|----------|
| `tuple[T, ...]` | Fixed-length or homogeneous immutable sequence |
| `Sequence[T]` | Read-only view (caller shouldn't mutate) |
| `list[T]` | Caller explicitly needs mutation |
| `frozenset[T]` | Immutable set |
| `Mapping[K, V]` | Read-only dict view |

```python
# Good: Returns immutable, caller can't accidentally mutate
def get_valid_users(users: list[User]) -> tuple[User, ...]:
    return tuple(u for u in users if u.is_valid)

# Risky: Returns mutable, leaks internal state
def get_valid_users(users: list[User]) -> list[User]:
    return [u for u in users if u.is_valid]
```

### 5. Dataclass vs NamedTuple

| Use | Type | Rationale |
|-----|------|-----------|
| Mutable domain objects | `@dataclass` | Needs modification |
| Immutable value objects | `@dataclass(frozen=True)` | Hashable, safe |
| Simple immutable records | `NamedTuple` | Lighter weight, tuple semantics |
| Config/settings | `@dataclass(frozen=True)` | Prevent runtime changes |

```python
from typing import NamedTuple
from dataclasses import dataclass

# NamedTuple: Simple, immutable, tuple semantics
class Point(NamedTuple):
    x: float
    y: float

# Frozen dataclass: More features, still immutable
@dataclass(frozen=True)
class User:
    id: str
    email: str

# Mutable dataclass: When mutation is required
@dataclass
class Order:
    id: str
    status: str = "pending"
```

### 6. Enforcement Limitations

| Pattern | Enforcement | Note |
|---------|-------------|------|
| Mutable defaults | Ruff B006, B039, RUF008, RUF012 | Automated |
| SequenceNotStr | mypy + useful-types | Type checker |
| Tuple over list.append | CLAUDE.md guidance | No Ruff rule exists |
| NamedTuple preference | CLAUDE.md guidance | Contextual decision |
| frozen=True | CLAUDE.md guidance | No Ruff rule exists |

### 7. CLAUDE.md Guidance (Required)

Add to consumer CLAUDE.md:

```markdown
## Immutability Patterns

| Prefer | Over | Why |
|--------|------|-----|
| `tuple(items)` | `list.append()` loop | Immutable result |
| `NamedTuple` | `dataclass` (for simple records) | Immutable by default |
| `@dataclass(frozen=True)` | `@dataclass` | Immutable objects |
| `SequenceNotStr[str]` | `Sequence[str]` | Prevents str-as-sequence bug |
| `frozenset()` | `set()` | Immutable sets |
| `Mapping[K, V]` | `dict[K, V]` (return type) | Read-only contract |
```

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| No enforcement | Bugs from mutability are common |
| Custom Ruff plugin for tuple | Complexity, maintenance burden |
| attrs everywhere | Less familiar than dataclass/NamedTuple |
| Strict immutability only | Some mutation is necessary |

## Consequences

### Positive

- Fewer mutation-related bugs
- Clearer function contracts
- SequenceNotStr prevents common footgun
- Consistent patterns across codebase
- Hashable objects when needed

### Negative

- Learning curve for patterns
- Some valid use cases need exceptions
- useful-types dependency

### Risks

| Risk | Mitigation |
|------|------------|
| Over-application of frozen | Document when mutation is appropriate |
| Performance (tuple creation) | Negligible for most cases; profile if needed |
| useful-types abandonment | Simple protocol, easy to vendor |

## References

- [Python typing footgun: Sequence[str]](https://github.com/python/typing/issues/256)
- [useful-types package](https://github.com/hauntsaninja/useful_types)
- [Ruff B006 mutable-argument-default](https://docs.astral.sh/ruff/rules/mutable-argument-default/)
- [PEP 557 - Data Classes](https://peps.python.org/pep-0557/)

## Approval Checklist

- [ ] Ruff B006, B039, RUF008, RUF012 enabled
- [ ] useful-types added to prescribed dependencies
- [ ] CLAUDE.md updated with immutability patterns
- [ ] Existing codebase reviewed for violations
