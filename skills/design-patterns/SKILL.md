---
name: Python Design Patterns
description: >
  This skill should be used when the user asks about "design patterns",
  "SOLID principles", "factory pattern", "strategy pattern", "observer pattern",
  "composition vs inheritance", "Pythonic design", "singleton alternatives",
  "anti-patterns", "dependency injection", or needs guidance on applying
  Gang of Four patterns idiomatically in Python.
---

# Python Design Patterns

This skill provides Pythonic adaptations of Gang of Four patterns, SOLID principles, and anti-patterns to avoid. Based on guidance from Brandon Rhodes, Raymond Hettinger, and the Python community.

> "Modern Python simply avoids the problems that the old design patterns were meant to solve."
> — Brandon Rhodes, PyCon 2025

## Quick Reference

| Pattern | Pythonic Approach | When to Use |
|---------|-------------------|-------------|
| **Factory** | Function returning instance | Multiple creation strategies |
| **Abstract Factory** | Dict of callables, module namespace | Family of related objects |
| **Builder** | `@dataclass` + `replace()`, fluent methods | Complex object construction |
| **Strategy** | First-class functions, `Callable` | Algorithm selection at runtime |
| **Observer** | Callbacks, `weakref.WeakSet` | Event notification |
| **Decorator** | `@decorator` syntax | Cross-cutting concerns |
| **Iterator** | Generators (`yield`), `__iter__` | Lazy sequence traversal |
| **Composite** | Recursive types | Tree-like structures |
| **Flyweight** | `__slots__`, `lru_cache`, interning | Memory optimization |
| **Command** | Callable objects, `functools.partial` | Encapsulate operations |
| **State** | Dict mapping states to handlers | State machines |
| **Singleton** | Module-level instance | Global state (rarely needed) |

## SOLID Principles

| Principle | Python Implementation |
|-----------|----------------------|
| **S**ingle Responsibility | One class = one reason to change |
| **O**pen-Closed | Extend via composition, not modification |
| **L**iskov Substitution | Subclass must honor parent's contract |
| **I**nterface Segregation | Small `Protocol` classes, not god-interfaces |
| **D**ependency Inversion | Depend on `Protocol`, not concrete class |

For detailed examples, see `references/solid-principles.md`.

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Python Alternative |
|--------------|---------|-------------------|
| Singleton class | Unnecessary complexity | Module-level instance |
| Deep inheritance | Tight coupling, fragility | Composition + protocols |
| Java getters/setters | Boilerplate | `@property` decorator |
| God Object | Violates SRP | Split into focused classes |
| Method could be function | Unused `self` | Module-level function |

For detailed examples, see `references/anti-patterns.md`.

## Pattern Categories

### Creational Patterns

Use when object creation logic is complex or needs flexibility.

```python
# Factory function - simple and testable
def create_user(name: str, role: str = "member") -> User:
    return User(name=name, role=role)

# Abstract Factory - dict of callables
EXPORTERS: dict[str, Callable[[], Exporter]] = {
    "json": JSONExporter,
    "csv": CSVExporter,
}
exporter = EXPORTERS[format_type]()
```

See `references/creational-patterns.md` for Builder and advanced factories.

### Behavioral Patterns

Use when you need flexible algorithms or event handling.

```python
# Strategy - pass functions, not strategy objects
def process_data(
    data: list[dict],
    transform: Callable[[dict], dict],
) -> list[dict]:
    return [transform(item) for item in data]

# Observer - simple callback list
class EventEmitter:
    def __init__(self) -> None:
        self._listeners: list[Callable[[Event], None]] = []

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        self._listeners.append(callback)
```

See `references/behavioral-patterns.md` for Iterator, Command, State.

### Structural Patterns

Use for object composition and interface adaptation.

```python
# Decorator - use Python's decorator syntax
from functools import wraps

def log_calls(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        log.info("calling", func=func.__name__)
        return func(*args, **kwargs)
    return wrapper
```

See `references/structural-patterns.md` for Composite, Flyweight, Adapter.

### Python-Specific Idioms

Patterns unique to Python's dynamic nature.

```python
# Global Object - module-level instance (not a singleton class)
# config.py
_config: Config | None = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config

# Sentinel - distinguish None from "not provided"
_MISSING = object()

def get_value(key: str, default: object = _MISSING) -> object:
    if key in cache:
        return cache[key]
    if default is _MISSING:
        raise KeyError(key)
    return default
```

See `references/python-idioms.md` for Prebound Method and more.

## When NOT to Use Patterns

| Situation | Guidance |
|-----------|----------|
| Simple instantiation | Don't use Factory; use `__init__` |
| Single implementation | Don't use Strategy; just call the function |
| No state sharing | Don't use Flyweight; regular objects are fine |
| No observers | Don't use Observer; direct calls are clearer |
| YAGNI applies | Don't add patterns for hypothetical futures |

## Reference Files

| File | Content |
|------|---------|
| `references/solid-principles.md` | Detailed SOLID with Python examples |
| `references/anti-patterns.md` | What to avoid with alternatives |
| `references/creational-patterns.md` | Factory, Builder patterns |
| `references/structural-patterns.md` | Composite, Decorator, Flyweight |
| `references/behavioral-patterns.md` | Strategy, Observer, Iterator, Command, State |
| `references/python-idioms.md` | Global Object, Prebound Method, Sentinel |

## Related Project Documentation

- [ADR-011](../../docs/adr/011-type-import-standards.md) - Protocol usage for interface segregation
- [ADR-013](../../docs/adr/013-immutability-safety-patterns.md) - Immutability patterns
- [ADR-014](../../docs/adr/014-design-patterns-skill.md) - Design decisions for this skill
