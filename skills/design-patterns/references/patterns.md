# Pythonic Design Patterns

Condensed GoF patterns adapted for Python. One example per pattern showing the Pythonic idiom.

## Creational Patterns

### Factory

```python
# Function factory (preferred over factory classes)
def create_connection(db_type: str) -> Connection:
    factories = {"postgres": PostgresConnection, "sqlite": SQLiteConnection}
    return factories[db_type]()

# Class factory methods
class User:
    @classmethod
    def admin(cls, name: str) -> User:
        return cls(name, role="admin")

    @classmethod
    def from_dict(cls, data: dict) -> User:
        return cls(**data)
```

### Abstract Factory

```python
# Dict of callables for related object families
EXPORTERS: dict[str, Callable[[], Exporter]] = {
    "json": JSONExporter,
    "csv": CSVExporter,
}
exporter = EXPORTERS[format_type]()

# Or use module namespaces: import themes.dark as theme; theme.Button()
```

### Builder

```python
# Immutable builder with dataclass + replace()
@dataclass(frozen=True)
class Email:
    to: str
    subject: str = ""
    body: str = ""
    cc: tuple[str, ...] = ()

msg = Email(to="user@example.com")
msg = replace(msg, subject="Hello", body="Welcome")

# Fluent builder: return self from each method
```

## Structural Patterns

### Decorator

```python
# Function decorator (most common)
def timing(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()
        result = func(*args, **kwargs)
        log.info("timing", func=func.__name__, elapsed=perf_counter() - start)
        return result
    return wrapper

@timing
def fetch_data(url: str) -> dict: ...
```

### Composite

```python
# Recursive dataclass with __iter__
@dataclass
class Directory:
    name: str
    children: list[File | Directory] = field(default_factory=list)

    def total_size(self) -> int:
        return sum(c.total_size() for c in self.children)

    def __iter__(self) -> Iterator[File]:
        for child in self.children:
            yield from child
```

### Flyweight

```python
# __slots__ for memory (56 bytes vs 300 bytes per instance)
class Point:
    __slots__ = ("x", "y")

# lru_cache for object reuse
@lru_cache(maxsize=1000)
def get_color(r: int, g: int, b: int) -> Color:
    return Color(r, g, b)
```

### Adapter

```python
# Wrapper class for interface conversion
@dataclass
class LegacyPrinterAdapter:
    legacy: LegacyPrinter

    def print(self, content: str) -> None:  # Modern interface
        self.legacy.print_document(content)  # Legacy method

# Function adapter
def adapt_fetch(fn: Callable[[int], dict]) -> Callable[[int], User]:
    return lambda uid: User(**fn(uid))
```

### Facade

```python
# Unified interface over complex subsystem
class MediaPlayer:
    def __init__(self) -> None:
        self._video, self._audio = VideoDecoder(), AudioDecoder()

    def play(self, path: Path) -> None:
        data = path.read_bytes()
        self._render(self._video.decode(data), self._audio.decode(data))
```

## Behavioral Patterns

### Strategy

```python
# Pass functions, not strategy objects
def calculate_total(items: list[Item], pricing: Callable[[float], float]) -> float:
    return sum(pricing(item.price) for item in items)

# Usage
total = calculate_total(items, lambda p: p * 0.9)  # 10% discount
total = calculate_total(items, lambda p: p)        # Regular price
```

### Observer

```python
# Simple callback list
@dataclass
class EventEmitter:
    _listeners: dict[str, list[Callable]] = field(default_factory=dict)

    def on(self, event: str, fn: Callable) -> None:
        self._listeners.setdefault(event, []).append(fn)

    def emit(self, event: str, *args) -> None:
        for fn in self._listeners.get(event, []):
            fn(*args)
```

### Iterator

```python
# Generator for lazy sequences
def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open() as f:
        for line in f:
            yield json.loads(line)

# Custom __iter__ for complex traversal
class TreeNode:
    def __iter__(self) -> Iterator[int]:
        yield self.value
        for child in self.children:
            yield from child
```

### Command

```python
# Callable commands with partial
commands: list[Callable[[], None]] = [
    partial(save_doc, doc, path),
    partial(send_email, doc, "user@example.com"),
]
for cmd in commands:
    cmd()

# For undo: dataclass with execute() and undo() methods
```

### State

```python
# Dict-based state machine
STATE_HANDLERS: dict[tuple[State, str], Callable[[Order], None]] = {
    (State.PENDING, "pay"): lambda o: setattr(o, "state", State.PAID),
    (State.PAID, "ship"): lambda o: setattr(o, "state", State.SHIPPED),
}

def transition(order: Order, action: str) -> None:
    handler = STATE_HANDLERS.get((order.state, action))
    if handler:
        handler(order)
```

## Pattern Selection

| Need | Pattern | Python Idiom |
|------|---------|--------------|
| Multiple creation strategies | Factory | Function or `@classmethod` |
| Complex object, many options | Builder | `dataclass` + `replace()` |
| Interchangeable algorithms | Strategy | Pass `Callable` |
| Event notification | Observer | Callback list |
| Lazy sequences | Iterator | Generator (`yield`) |
| Tree structures | Composite | Recursive dataclass |
| Memory optimization | Flyweight | `__slots__`, `lru_cache` |
| Interface conversion | Adapter | Wrapper class |
| Cross-cutting concerns | Decorator | `@decorator` |
| State machines | State | Dict mapping |
