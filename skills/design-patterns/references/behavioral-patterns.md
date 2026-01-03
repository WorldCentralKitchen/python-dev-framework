# Behavioral Patterns in Python

Patterns for algorithm selection, event handling, and object interaction.

## Strategy Pattern

Encapsulate interchangeable algorithms. In Python, use first-class functions.

```python
# Traditional OOP approach (verbose)
from typing import Protocol

class PricingStrategy(Protocol):
    def calculate(self, base_price: float) -> float: ...

class RegularPricing:
    def calculate(self, base_price: float) -> float:
        return base_price

class DiscountPricing:
    def calculate(self, base_price: float) -> float:
        return base_price * 0.9
```

```python
# PYTHONIC: Functions as strategies
from collections.abc import Callable

PricingFn = Callable[[float], float]

def regular_pricing(base_price: float) -> float:
    return base_price

def discount_pricing(base_price: float) -> float:
    return base_price * 0.9

def vip_pricing(discount_pct: float) -> PricingFn:
    def calculate(base_price: float) -> float:
        return base_price * (1 - discount_pct / 100)
    return calculate

# Usage
def calculate_total(items: list[Item], pricing: PricingFn) -> float:
    return sum(pricing(item.price) for item in items)

total = calculate_total(items, discount_pricing)
total_vip = calculate_total(items, vip_pricing(20))
```

**When to use Strategy:**
- Multiple algorithms for the same task
- Algorithm selection at runtime
- Avoid switch/if-elif chains on type

## Observer Pattern

Notify multiple objects of state changes. Use callbacks or weak references.

```python
# Simple callback implementation
from collections.abc import Callable
from dataclasses import dataclass, field

@dataclass
class EventEmitter:
    _listeners: dict[str, list[Callable]] = field(default_factory=dict)

    def on(self, event: str, callback: Callable) -> None:
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable) -> None:
        if event in self._listeners:
            self._listeners[event].remove(callback)

    def emit(self, event: str, *args, **kwargs) -> None:
        for callback in self._listeners.get(event, []):
            callback(*args, **kwargs)

# Usage
emitter = EventEmitter()
emitter.on("user_created", lambda user: send_welcome_email(user))
emitter.on("user_created", lambda user: log.info("created", user=user.id))
emitter.emit("user_created", new_user)
```

```python
# Weak reference for automatic cleanup
import weakref
from collections.abc import Callable

class WeakEventEmitter:
    def __init__(self) -> None:
        self._listeners: dict[str, weakref.WeakSet] = {}

    def subscribe(self, event: str, listener: object) -> None:
        if event not in self._listeners:
            self._listeners[event] = weakref.WeakSet()
        self._listeners[event].add(listener)

    def emit(self, event: str, *args) -> None:
        for listener in self._listeners.get(event, []):
            listener.handle(event, *args)
```

**When to use Observer:**
- Decoupled event notification
- Multiple handlers for same event
- Publish/subscribe semantics

## Iterator Pattern

Python has built-in iteration. Use generators for lazy sequences.

```python
# Built-in iteration (preferred)
class TreeNode:
    def __init__(self, value: int, children: list[TreeNode] | None = None):
        self.value = value
        self.children = children or []

    def __iter__(self) -> Iterator[int]:
        yield self.value
        for child in self.children:
            yield from child  # Recursive iteration

# Usage
root = TreeNode(1, [TreeNode(2), TreeNode(3, [TreeNode(4)])])
for value in root:
    print(value)  # 1, 2, 3, 4
```

```python
# Generator for lazy evaluation
def read_large_file(path: Path) -> Iterator[dict]:
    with path.open() as f:
        for line in f:
            yield json.loads(line)

# Only loads one line at a time
for record in read_large_file(huge_file):
    process(record)
```

```python
# Custom iterator class (when state is complex)
@dataclass
class Paginator:
    items: list[T]
    page_size: int = 10

    def __iter__(self) -> Iterator[list[T]]:
        for i in range(0, len(self.items), self.page_size):
            yield self.items[i:i + self.page_size]

for page in Paginator(all_users, page_size=50):
    process_batch(page)
```

**When to use Iterator:**
- Large datasets (lazy evaluation)
- Custom traversal order
- Streaming data

## Command Pattern

Encapsulate operations as objects. Use callables or dataclasses.

```python
# Callable command (simplest)
from functools import partial

def save_document(doc: Document, path: Path) -> None:
    path.write_text(doc.content)

def email_document(doc: Document, to: str) -> None:
    mailer.send(to, doc.content)

# Command queue
commands: list[Callable[[], None]] = [
    partial(save_document, doc, backup_path),
    partial(email_document, doc, "user@example.com"),
]

for command in commands:
    command()
```

```python
# Command with undo (when history needed)
from abc import ABC, abstractmethod
from dataclasses import dataclass

class Command(ABC):
    @abstractmethod
    def execute(self) -> None: ...

    @abstractmethod
    def undo(self) -> None: ...

@dataclass
class SetTextCommand(Command):
    editor: TextEditor
    new_text: str
    old_text: str = field(init=False)

    def execute(self) -> None:
        self.old_text = self.editor.text
        self.editor.text = self.new_text

    def undo(self) -> None:
        self.editor.text = self.old_text

class CommandHistory:
    def __init__(self) -> None:
        self._history: list[Command] = []

    def execute(self, command: Command) -> None:
        command.execute()
        self._history.append(command)

    def undo(self) -> None:
        if self._history:
            self._history.pop().undo()
```

**When to use Command:**
- Undo/redo functionality
- Command queuing or scheduling
- Macro recording

## State Pattern

Object behavior changes based on internal state. Use dict mapping or enum + match.

```python
# Dict-based state machine
from enum import Enum, auto
from collections.abc import Callable

class OrderState(Enum):
    PENDING = auto()
    PAID = auto()
    SHIPPED = auto()
    DELIVERED = auto()

@dataclass
class Order:
    id: str
    state: OrderState = OrderState.PENDING

    def transition(self, action: str) -> None:
        handler = STATE_HANDLERS.get((self.state, action))
        if handler is None:
            raise ValueError(f"Invalid action {action} for state {self.state}")
        handler(self)

def _pay_order(order: Order) -> None:
    order.state = OrderState.PAID
    log.info("order_paid", order_id=order.id)

def _ship_order(order: Order) -> None:
    order.state = OrderState.SHIPPED
    notify_customer(order)

STATE_HANDLERS: dict[tuple[OrderState, str], Callable[[Order], None]] = {
    (OrderState.PENDING, "pay"): _pay_order,
    (OrderState.PAID, "ship"): _ship_order,
    (OrderState.SHIPPED, "deliver"): lambda o: setattr(o, "state", OrderState.DELIVERED),
}
```

```python
# Match statement (Python 3.10+)
def process_order(order: Order, action: str) -> None:
    match (order.state, action):
        case (OrderState.PENDING, "pay"):
            order.state = OrderState.PAID
        case (OrderState.PAID, "ship"):
            order.state = OrderState.SHIPPED
        case (OrderState.SHIPPED, "deliver"):
            order.state = OrderState.DELIVERED
        case _:
            raise ValueError(f"Invalid transition: {order.state} + {action}")
```

**When to use State:**
- Object behavior depends on state
- Many conditional branches on state
- State transitions need validation

## Summary Table

| Pattern | Python Idiom | Use Case |
|---------|--------------|----------|
| Strategy | Functions, `Callable` | Interchangeable algorithms |
| Observer | Callback lists, `weakref` | Event notification |
| Iterator | Generators, `__iter__` | Lazy sequences |
| Command | `partial`, callable dataclass | Undo/redo, queuing |
| State | Dict mapping, match | State machines |
