# SOLID Principles & Anti-Patterns

## SOLID Principles

| Principle | Violation Sign | Python Solution |
|-----------|----------------|-----------------|
| **S**ingle Responsibility | "Manager" class, many unrelated methods | Split into focused classes |
| **O**pen-Closed | `if/elif` chains for types | Dict of handlers + Protocol |
| **L**iskov Substitution | `NotImplementedError` in subclass | Composition over inheritance |
| **I**nterface Segregation | Unused methods forced by interface | Small `Protocol` classes |
| **D**ependency Inversion | `self.db = PostgresDB()` in __init__ | Constructor injection + Protocol |

### Single Responsibility

```python
# GOOD: One class = one reason to change
class UserRepository:
    def create(self, data: dict) -> User: ...
    def find_by_id(self, id: str) -> User | None: ...

class EmailService:
    def send_welcome(self, user: User) -> None: ...
```

### Open-Closed

```python
# GOOD: Extend via dict, not modification
class Exporter(Protocol):
    def export(self, data: Report) -> bytes: ...

EXPORTERS: dict[str, type[Exporter]] = {"pdf": PDFExporter, "csv": CSVExporter}
# Adding JSON: just add to dict, don't modify existing code
```

### Liskov Substitution

```python
# GOOD: Separate types with shared Protocol (not Square extends Rectangle)
class Shape(Protocol):
    def area(self) -> float: ...

@dataclass(frozen=True)
class Rectangle:
    width: float
    height: float
    def area(self) -> float: return self.width * self.height

@dataclass(frozen=True)
class Square:
    side: float
    def area(self) -> float: return self.side ** 2
```

### Interface Segregation

```python
# GOOD: Small, focused protocols
class Workable(Protocol):
    def work(self) -> None: ...

class Codeable(Protocol):
    def code(self) -> None: ...

# Classes implement only what they need
```

### Dependency Inversion

```python
# GOOD: Depend on Protocol, inject implementations
class Database(Protocol):
    def save(self, entity: object) -> None: ...

class OrderProcessor:
    def __init__(self, db: Database) -> None:  # Inject, don't create
        self.db = db
```

---

## Anti-Patterns

| Anti-Pattern | Why Bad | Pythonic Alternative |
|--------------|---------|---------------------|
| Singleton class | Modules ARE singletons | Module-level instance |
| Deep inheritance | Tight coupling, diamond problem | Composition + Protocol |
| Java getters/setters | Boilerplate | Direct attrs, `@property` if needed |
| God Object | SRP violation, untestable | Split into focused classes |
| Method without self | Unnecessary class | Module-level function |
| Premature patterns | Over-engineering | Add patterns when needed (YAGNI) |

### Singleton → Module Instance

```python
# BAD: Singleton class with __new__
# GOOD: Module-level instance
_config: Config | None = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
```

### Inheritance → Composition

```python
# BAD: class Dolphin(Mammal, Swimmer) - hierarchy explosion
# GOOD: Composition with protocols
class CanSwim(Protocol):
    def swim(self) -> None: ...

@dataclass
class Dolphin:  # No inheritance needed
    name: str
    def swim(self) -> None: ...
```

### Java Getters/Setters → Direct Access

```python
# BAD: get_name() / set_name()
# GOOD: Direct attribute access
user.name = "Alice"

# Add @property later if validation needed (interface unchanged)
```

### God Object → Focused Services

```python
# BAD: Application with create_user, send_email, process_payment, ...
# GOOD: Separate services
class Application:
    def __init__(self) -> None:
        self.users = UserService(db)
        self.payments = PaymentService(db)
```

### Method Without Self → Function

```python
# BAD: class MathUtils with add(self, a, b)
# GOOD: Module-level function
def add(a: int, b: int) -> int:
    return a + b
```
