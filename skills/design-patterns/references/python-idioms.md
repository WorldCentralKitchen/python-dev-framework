# Python-Specific Idioms

Design patterns unique to Python's dynamic nature.

## Global Object Pattern

Module-level instances for shared state. Python modules are singletons.

```python
# config.py - Lazy initialization
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    database_url: str
    debug: bool
    log_level: str

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            database_url=os.environ["DATABASE_URL"],
            debug=os.environ.get("DEBUG", "false").lower() == "true",
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

_config: Config | None = None

def get_config() -> Config:
    """Get or create the global config."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config

def reset_config() -> None:
    """Reset for testing."""
    global _config
    _config = None
```

```python
# Connection pool - Eager initialization
# db.py
from contextlib import contextmanager
from typing import Iterator

class ConnectionPool:
    def __init__(self, url: str, size: int = 10) -> None:
        self.url = url
        self.size = size
        self._connections: list[Connection] = []

    def acquire(self) -> Connection: ...
    def release(self, conn: Connection) -> None: ...

# Module-level instance (created at import time)
pool = ConnectionPool(
    url=os.environ.get("DATABASE_URL", "sqlite:///dev.db"),
    size=int(os.environ.get("POOL_SIZE", "10")),
)

@contextmanager
def get_connection() -> Iterator[Connection]:
    conn = pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)
```

```python
# Logger - Standard library example
import structlog

# Module-level logger (this IS the pattern)
log = structlog.get_logger()

def process_order(order: Order) -> None:
    log.info("processing_order", order_id=order.id)
```

**When to use Global Object:**
- Configuration that doesn't change at runtime
- Connection pools and resource managers
- Loggers and metrics collectors

**Avoid when:**
- State changes during execution (use dependency injection)
- Testing requires different configurations (provide reset/override)

## Prebound Method Pattern

Bind methods to instances for later use. Use `functools.partial` or method references.

```python
# Method reference
class Processor:
    def __init__(self, multiplier: int) -> None:
        self.multiplier = multiplier

    def process(self, value: int) -> int:
        return value * self.multiplier

processor = Processor(10)

# Prebound method - carries instance reference
process_fn = processor.process
result = process_fn(5)  # 50

# Use as callback
results = list(map(processor.process, [1, 2, 3]))  # [10, 20, 30]
```

```python
# functools.partial for parameter binding
from functools import partial

def send_email(to: str, subject: str, body: str) -> None:
    log.info("sending", to=to, subject=subject)

# Prebind parameters
send_welcome = partial(send_email, subject="Welcome!", body="Thanks for joining")
send_welcome(to="user@example.com")

# Prebind with keyword arguments
send_alert = partial(send_email, subject="ALERT")
send_alert(to="admin@example.com", body="Server down")
```

```python
# Event handlers
from dataclasses import dataclass, field
from collections.abc import Callable

@dataclass
class Button:
    label: str
    on_click: Callable[[], None] = lambda: None

class App:
    def __init__(self) -> None:
        self.counter = 0

    def increment(self) -> None:
        self.counter += 1
        log.info("incremented", counter=self.counter)

    def decrement(self) -> None:
        self.counter -= 1
        log.info("decremented", counter=self.counter)

app = App()

# Prebound methods as callbacks
buttons = [
    Button("+", on_click=app.increment),  # Bound method
    Button("-", on_click=app.decrement),
]
```

**When to use Prebound Method:**
- Callbacks and event handlers
- Delayed execution with captured state
- Partial application of methods

## Sentinel Object Pattern

Distinguish "no value" from `None`. Use unique objects.

```python
# Basic sentinel
_MISSING = object()

def get_config_value(key: str, default: object = _MISSING) -> object:
    """Get config value, raise if missing and no default."""
    value = config.get(key)
    if value is not None:
        return value
    if default is _MISSING:
        raise KeyError(f"Missing required config: {key}")
    return default

# None is a valid value, sentinel distinguishes "not provided"
get_config_value("debug")  # Raises if missing
get_config_value("debug", None)  # Returns None if missing
get_config_value("debug", False)  # Returns False if missing
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

def find_user(user_id: str) -> User | _Sentinel:
    user = db.find(user_id)
    if user is None:
        return NOT_FOUND
    return user

result = find_user("123")
if result is NOT_FOUND:
    log.warning("user_not_found", user_id="123")
```

```python
# Dataclass with optional fields
from dataclasses import dataclass, field

_UNSET = object()

@dataclass
class UpdateUserRequest:
    # None means "set to null", UNSET means "don't change"
    name: str | None | object = _UNSET
    email: str | None | object = _UNSET
    bio: str | None | object = _UNSET

def update_user(user: User, request: UpdateUserRequest) -> User:
    if request.name is not _UNSET:
        user.name = request.name  # Could be None (clear) or string
    if request.email is not _UNSET:
        user.email = request.email
    if request.bio is not _UNSET:
        user.bio = request.bio
    return user
```

**When to use Sentinel:**
- `None` is a valid value
- Distinguish "not provided" from "explicitly null"
- Optional parameters with `None` as meaningful value

## EAFP vs LBYL

Easier to Ask Forgiveness than Permission vs Look Before You Leap.

```python
# LBYL - Check first (non-Pythonic)
def get_value_lbyl(d: dict, key: str) -> str | None:
    if key in d:  # Check
        return d[key]  # Then access
    return None

# EAFP - Try and catch (Pythonic)
def get_value_eafp(d: dict, key: str) -> str | None:
    try:
        return d[key]  # Just do it
    except KeyError:
        return None  # Handle exception
```

```python
# EAFP for file operations
# Pythonic
def read_config() -> dict:
    try:
        with open("config.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        log.error("invalid_config", error=str(e))
        return {}

# LBYL (race condition risk)
def read_config_lbyl() -> dict:
    if os.path.exists("config.json"):  # File could be deleted here!
        with open("config.json") as f:
            return json.load(f)
    return {}
```

```python
# EAFP for type checking
def process_items(items: object) -> list[str]:
    try:
        return [str(item) for item in items]  # Assume iterable
    except TypeError:
        return [str(items)]  # Handle non-iterable
```

**EAFP Advantages:**
- Avoids race conditions
- Often faster (no redundant checks)
- More Pythonic

**Use LBYL when:**
- Operations have side effects
- Exception handling is expensive
- Validation for user feedback

## Duck Typing

"If it walks like a duck and quacks like a duck..."

```python
# Protocol for structural typing
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

class Circle:
    def draw(self) -> None:
        print("Drawing circle")

class Square:
    def draw(self) -> None:
        print("Drawing square")

def render(shape: Drawable) -> None:
    shape.draw()  # Works with any object that has draw()

# No inheritance required!
render(Circle())
render(Square())
```

```python
# File-like objects
from typing import Protocol

class Readable(Protocol):
    def read(self, n: int = -1) -> str: ...

def process_input(source: Readable) -> str:
    return source.read()

# Works with files
with open("data.txt") as f:
    process_input(f)

# Works with StringIO
from io import StringIO
process_input(StringIO("test data"))

# Works with any object with read()
class CustomReader:
    def read(self, n: int = -1) -> str:
        return "custom data"

process_input(CustomReader())
```

**Duck Typing Guidelines:**
- Define `Protocol` for type checking
- Don't use `isinstance()` checks unless necessary
- Focus on behavior, not identity

## Summary Table

| Pattern | Python Idiom | Use Case |
|---------|--------------|----------|
| Global Object | Module-level instance, lazy init | Shared configuration, pools |
| Prebound Method | `method_ref`, `partial` | Callbacks, event handlers |
| Sentinel | `object()`, custom sentinel class | Distinguish None from unset |
| EAFP | `try/except` | File ops, dict access |
| Duck Typing | `Protocol`, structural typing | Flexible interfaces |
