# Structural Patterns in Python

Patterns for object composition and interface adaptation.

## Decorator Pattern

Add behavior to objects dynamically. Distinct from Python's `@decorator` syntax.

```python
# Python function decorator (most common)
from functools import wraps
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def log_calls(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        log.info("calling", func=func.__name__, args=args)
        result = func(*args, **kwargs)
        log.info("returned", func=func.__name__, result=result)
        return result
    return wrapper

@log_calls
def calculate_total(items: list[Item]) -> float:
    return sum(item.price for item in items)
```

```python
# Stacking decorators
from time import perf_counter

def timing(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        log.info("timing", func=func.__name__, elapsed_ms=elapsed * 1000)
        return result
    return wrapper

def retry(attempts: int = 3) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts - 1:
                        raise
                    log.warning("retry", attempt=attempt, error=str(e))
            raise RuntimeError("Unreachable")
        return wrapper
    return decorator

@timing
@retry(attempts=3)
def fetch_data(url: str) -> dict:
    return requests.get(url).json()
```

```python
# Class-based decorator (when state needed)
from typing import Protocol

class TextComponent(Protocol):
    def render(self) -> str: ...

@dataclass
class PlainText:
    text: str

    def render(self) -> str:
        return self.text

@dataclass
class BoldDecorator:
    wrapped: TextComponent

    def render(self) -> str:
        return f"<b>{self.wrapped.render()}</b>"

@dataclass
class ItalicDecorator:
    wrapped: TextComponent

    def render(self) -> str:
        return f"<i>{self.wrapped.render()}</i>"

# Usage
text = ItalicDecorator(BoldDecorator(PlainText("Hello")))
print(text.render())  # <i><b>Hello</b></i>
```

**When to use Decorator:**
- Add behavior without modifying original
- Cross-cutting concerns (logging, timing, caching)
- Behavior can be stacked

## Composite Pattern

Treat individual objects and compositions uniformly. Use recursive types.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterator

@dataclass
class File:
    name: str
    size: int

    def total_size(self) -> int:
        return self.size

    def __iter__(self) -> Iterator[File]:
        yield self

@dataclass
class Directory:
    name: str
    children: list[File | Directory] = field(default_factory=list)

    def total_size(self) -> int:
        return sum(child.total_size() for child in self.children)

    def __iter__(self) -> Iterator[File]:
        for child in self.children:
            yield from child

    def add(self, child: File | Directory) -> None:
        self.children.append(child)

# Usage
root = Directory("root")
root.add(File("readme.txt", 100))

src = Directory("src")
src.add(File("main.py", 500))
src.add(File("utils.py", 200))
root.add(src)

print(root.total_size())  # 800
for file in root:
    print(file.name)  # readme.txt, main.py, utils.py
```

```python
# UI component tree
from abc import ABC, abstractmethod

class Component(ABC):
    @abstractmethod
    def render(self) -> str: ...

@dataclass
class Text(Component):
    content: str

    def render(self) -> str:
        return self.content

@dataclass
class Container(Component):
    children: list[Component] = field(default_factory=list)
    tag: str = "div"

    def render(self) -> str:
        inner = "".join(c.render() for c in self.children)
        return f"<{self.tag}>{inner}</{self.tag}>"

    def add(self, child: Component) -> Container:
        self.children.append(child)
        return self

# Build UI tree
page = Container(tag="html").add(
    Container(tag="body").add(
        Container(tag="header").add(Text("Welcome"))
    ).add(
        Container(tag="main").add(Text("Content here"))
    )
)
```

**When to use Composite:**
- Tree-like structures (file systems, UI, org charts)
- Operations on individual items and groups uniformly
- Recursive data structures

## Flyweight Pattern

Share state to reduce memory usage. Use `__slots__`, interning, or caching.

```python
# __slots__ for memory optimization
class Point:
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

# Without __slots__: ~300 bytes per instance
# With __slots__: ~56 bytes per instance
```

```python
# String interning
import sys

# Python automatically interns some strings
a = "hello"
b = "hello"
assert a is b  # Same object

# Manual interning for dynamic strings
cache: dict[str, str] = {}

def intern_string(s: str) -> str:
    if s not in cache:
        cache[s] = sys.intern(s)
    return cache[s]
```

```python
# Flyweight with factory
from functools import lru_cache

@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

@lru_cache(maxsize=1000)
def get_color(r: int, g: int, b: int) -> Color:
    return Color(r, g, b)

# Reuses same Color objects
red1 = get_color(255, 0, 0)
red2 = get_color(255, 0, 0)
assert red1 is red2  # Same object
```

```python
# Glyph flyweight (classic example)
@dataclass(frozen=True)
class Glyph:
    """Intrinsic state: shared across all uses."""
    char: str
    font: str
    size: int

@dataclass
class GlyphContext:
    """Extrinsic state: varies per use."""
    glyph: Glyph
    x: int
    y: int
    color: str

class GlyphFactory:
    _glyphs: dict[tuple, Glyph] = {}

    @classmethod
    def get(cls, char: str, font: str, size: int) -> Glyph:
        key = (char, font, size)
        if key not in cls._glyphs:
            cls._glyphs[key] = Glyph(char, font, size)
        return cls._glyphs[key]

# Render document - shares Glyph objects
def render_text(text: str) -> list[GlyphContext]:
    contexts = []
    for i, char in enumerate(text):
        glyph = GlyphFactory.get(char, "Arial", 12)
        contexts.append(GlyphContext(glyph, x=i*10, y=0, color="black"))
    return contexts
```

**When to use Flyweight:**
- Many similar objects consuming memory
- Intrinsic state (shared) vs extrinsic state (per-use)
- Immutable shared objects

## Adapter Pattern

Convert one interface to another. Use composition or Protocol wrappers.

```python
# Adapter wrapping legacy interface
class LegacyPrinter:
    def print_document(self, doc: str) -> None:
        print(f"Legacy printing: {doc}")

class ModernPrinter(Protocol):
    def print(self, content: str) -> None: ...

@dataclass
class LegacyPrinterAdapter:
    legacy: LegacyPrinter

    def print(self, content: str) -> None:
        self.legacy.print_document(content)

def print_all(printers: list[ModernPrinter], content: str) -> None:
    for printer in printers:
        printer.print(content)

# Usage
legacy = LegacyPrinter()
adapted = LegacyPrinterAdapter(legacy)
print_all([adapted], "Hello")
```

```python
# Function adapter
from collections.abc import Callable

# Legacy API returns dict
def legacy_fetch_user(user_id: int) -> dict:
    return {"id": user_id, "name": "Alice", "email": "alice@example.com"}

# Modern API expects User object
@dataclass
class User:
    id: int
    name: str
    email: str

def adapt_fetch(
    fetch_fn: Callable[[int], dict]
) -> Callable[[int], User]:
    def adapted(user_id: int) -> User:
        data = fetch_fn(user_id)
        return User(**data)
    return adapted

fetch_user = adapt_fetch(legacy_fetch_user)
user = fetch_user(123)  # Returns User object
```

**When to use Adapter:**
- Integrating incompatible interfaces
- Wrapping legacy code
- Third-party library integration

## Facade Pattern

Simplify complex subsystems with a unified interface.

```python
# Complex subsystem
class VideoDecoder:
    def decode(self, data: bytes) -> VideoFrame: ...

class AudioDecoder:
    def decode(self, data: bytes) -> AudioFrame: ...

class Renderer:
    def render(self, video: VideoFrame, audio: AudioFrame) -> None: ...

class FileReader:
    def read(self, path: Path) -> bytes: ...

# Simple facade
class MediaPlayer:
    def __init__(self) -> None:
        self._video = VideoDecoder()
        self._audio = AudioDecoder()
        self._renderer = Renderer()
        self._reader = FileReader()

    def play(self, path: Path) -> None:
        data = self._reader.read(path)
        video = self._video.decode(data)
        audio = self._audio.decode(data)
        self._renderer.render(video, audio)

# Usage - simple interface
player = MediaPlayer()
player.play(Path("movie.mp4"))
```

**When to use Facade:**
- Complex subsystem needs simple interface
- Reduce dependencies on subsystem internals
- Layer separation (API layer over implementation)

## Summary Table

| Pattern | Python Idiom | Use Case |
|---------|--------------|----------|
| Decorator | `@decorator`, wrapper class | Add behavior dynamically |
| Composite | Recursive dataclass, `__iter__` | Tree structures |
| Flyweight | `__slots__`, `lru_cache`, interning | Memory optimization |
| Adapter | Wrapper class, function adapter | Interface conversion |
| Facade | Unified class over subsystem | Simplify complex APIs |
