# Python-Specific Idioms

Patterns unique to Python's dynamic nature.

## Global Object Pattern

Module-level instances for shared state. Python modules are singletons (`sys.modules` caches imports).

```python
# Lazy initialization
_config: Config | None = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config

def reset_config() -> None:  # For testing
    global _config
    _config = None
```

```python
# Eager initialization (connection pools, loggers)
import structlog
log = structlog.get_logger()  # Module-level logger
```

| Use For | Avoid When |
|---------|------------|
| Config, loggers, connection pools | State changes at runtime |
| Resources initialized once | Testing needs isolation (add reset) |

## Prebound Method Pattern

Bind methods to instances for callbacks. Methods carry their instance reference.

```python
# Method reference as callback
processor = Processor(multiplier=10)
results = list(map(processor.process, [1, 2, 3]))  # [10, 20, 30]

# functools.partial for parameter binding
from functools import partial
send_welcome = partial(send_email, subject="Welcome!", body="Thanks")
send_welcome(to="user@example.com")
```

```python
# Event handlers
@dataclass
class Button:
    label: str
    on_click: Callable[[], None] = lambda: None

app = App()
buttons = [
    Button("+", on_click=app.increment),  # Bound method
    Button("-", on_click=app.decrement),
]
```

## Sentinel Object Pattern

Distinguish "no value" from `None` when `None` is valid.

```python
_MISSING = object()

def get_value(key: str, default: object = _MISSING) -> object:
    value = cache.get(key)
    if value is not None:
        return value
    if default is _MISSING:
        raise KeyError(key)
    return default

# None is valid: get_value("key", None) returns None if missing
# No default: get_value("key") raises if missing
```

```python
# Named sentinel for clarity
class _Sentinel:
    __slots__ = ("name",)
    def __init__(self, name: str) -> None:
        self.name = name
    def __repr__(self) -> str:
        return f"<{self.name}>"

UNSET = _Sentinel("UNSET")
NOT_FOUND = _Sentinel("NOT_FOUND")
```

| Use For | Example |
|---------|---------|
| Optional params where None is valid | `default=_MISSING` |
| Distinguish "not found" from "is None" | `return NOT_FOUND` |
| Partial updates (PATCH APIs) | `name: str | object = UNSET` |

## Summary

| Pattern | Python Idiom | Use Case |
|---------|--------------|----------|
| Global Object | Module-level instance | Config, pools, loggers |
| Prebound Method | `obj.method`, `partial` | Callbacks, event handlers |
| Sentinel | `_MISSING = object()` | Distinguish None from unset |
