# SOLID Principles in Python

Practical Python implementations of SOLID principles with good/bad examples.

## Single Responsibility Principle (SRP)

A class should have only one reason to change.

```python
# BAD: Multiple responsibilities
class UserManager:
    def create_user(self, data: dict) -> User: ...
    def send_welcome_email(self, user: User) -> None: ...
    def generate_report(self, users: list[User]) -> str: ...
    def backup_to_s3(self, users: list[User]) -> None: ...
```

```python
# GOOD: Single responsibility per class
class UserRepository:
    def create(self, data: dict) -> User: ...
    def find_by_id(self, user_id: str) -> User | None: ...

class EmailService:
    def send_welcome(self, user: User) -> None: ...

class UserReportGenerator:
    def generate(self, users: list[User]) -> str: ...
```

**Signs of SRP violation:**
- Class has many unrelated methods
- Changes to one feature require modifying unrelated code
- Hard to name the class without using "and" or "Manager"

## Open-Closed Principle (OCP)

Open for extension, closed for modification.

```python
# BAD: Modifying existing code for new formats
class ReportExporter:
    def export(self, data: Report, format: str) -> bytes:
        if format == "pdf":
            return self._to_pdf(data)
        elif format == "csv":
            return self._to_csv(data)
        elif format == "json":  # Added later - modifies class
            return self._to_json(data)
        raise ValueError(f"Unknown format: {format}")
```

```python
# GOOD: Extend via composition
from typing import Protocol

class Exporter(Protocol):
    def export(self, data: Report) -> bytes: ...

class PDFExporter:
    def export(self, data: Report) -> bytes: ...

class CSVExporter:
    def export(self, data: Report) -> bytes: ...

class JSONExporter:  # New format - no modification needed
    def export(self, data: Report) -> bytes: ...

# Registration pattern
EXPORTERS: dict[str, type[Exporter]] = {
    "pdf": PDFExporter,
    "csv": CSVExporter,
    "json": JSONExporter,
}
```

## Liskov Substitution Principle (LSP)

Subtypes must be substitutable for their base types.

```python
# BAD: Violates LSP - Square changes Rectangle's invariants
class Rectangle:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height

class Square(Rectangle):
    def __init__(self, side: float) -> None:
        super().__init__(side, side)

    @property
    def width(self) -> float:
        return self._side

    @width.setter
    def width(self, value: float) -> None:
        self._side = value  # Also changes height - unexpected!
```

```python
# GOOD: Separate types, shared protocol
from typing import Protocol

class Shape(Protocol):
    def area(self) -> float: ...

@dataclass(frozen=True)
class Rectangle:
    width: float
    height: float

    def area(self) -> float:
        return self.width * self.height

@dataclass(frozen=True)
class Square:
    side: float

    def area(self) -> float:
        return self.side ** 2

def total_area(shapes: Sequence[Shape]) -> float:
    return sum(s.area() for s in shapes)
```

**LSP Guidelines:**
- Preconditions cannot be strengthened in subtype
- Postconditions cannot be weakened in subtype
- Invariants must be preserved

## Interface Segregation Principle (ISP)

Clients shouldn't depend on interfaces they don't use.

```python
# BAD: Fat interface forces unused implementations
class Worker(Protocol):
    def work(self) -> None: ...
    def eat(self) -> None: ...
    def sleep(self) -> None: ...
    def code(self) -> None: ...
    def manage(self) -> None: ...

class Robot:  # Must implement eat/sleep even though N/A
    def eat(self) -> None:
        raise NotImplementedError  # Code smell!
```

```python
# GOOD: Small, focused protocols
class Workable(Protocol):
    def work(self) -> None: ...

class Codeable(Protocol):
    def code(self) -> None: ...

class Manageable(Protocol):
    def manage(self) -> None: ...

class Developer:
    def work(self) -> None: ...
    def code(self) -> None: ...

class Manager:
    def work(self) -> None: ...
    def manage(self) -> None: ...

class Robot:
    def work(self) -> None: ...
    # Only implements what it needs
```

**Python Approach:**
- Use `Protocol` for structural typing
- Define small, focused protocols
- Combine protocols with `Union` or multiple inheritance when needed

## Dependency Inversion Principle (DIP)

Depend on abstractions, not concretions.

```python
# BAD: Direct dependency on concrete implementation
class OrderProcessor:
    def __init__(self) -> None:
        self.db = PostgresDatabase()  # Concrete dependency
        self.mailer = SMTPMailer()    # Concrete dependency

    def process(self, order: Order) -> None:
        self.db.save(order)
        self.mailer.send_confirmation(order)
```

```python
# GOOD: Depend on protocols, inject implementations
from typing import Protocol

class Database(Protocol):
    def save(self, entity: object) -> None: ...

class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...

class OrderProcessor:
    def __init__(self, db: Database, mailer: Mailer) -> None:
        self.db = db
        self.mailer = mailer

    def process(self, order: Order) -> None:
        self.db.save(order)
        self.mailer.send(
            order.customer_email,
            "Order Confirmation",
            f"Order {order.id} confirmed",
        )

# Usage - inject concrete implementations
processor = OrderProcessor(
    db=PostgresDatabase(connection_string),
    mailer=SMTPMailer(smtp_config),
)

# Testing - inject test doubles
def test_order_processing() -> None:
    mock_db = MockDatabase()
    mock_mailer = MockMailer()
    processor = OrderProcessor(mock_db, mock_mailer)
    processor.process(test_order)
    assert mock_db.saved == [test_order]
```

**DIP Benefits:**
- Testable code (easy to inject mocks)
- Flexible configuration (swap implementations)
- Decoupled modules (no import of concrete classes)

## Summary Table

| Principle | Violation Sign | Python Solution |
|-----------|----------------|-----------------|
| SRP | "Manager" classes, many methods | Split into focused classes |
| OCP | `if/elif` chains for types | Dict of handlers, Protocol |
| LSP | `NotImplementedError` in subclass | Composition over inheritance |
| ISP | Unused methods in implementers | Small `Protocol` classes |
| DIP | `import ConcreteClass` in __init__ | Constructor injection + Protocol |
