# Creational Patterns in Python

Patterns for flexible object creation.

## Factory Method

Delegate instantiation to functions or methods. Python favors callable factories.

```python
# Simple factory function
def create_connection(db_type: str) -> Connection:
    match db_type:
        case "postgres":
            return PostgresConnection()
        case "sqlite":
            return SQLiteConnection()
        case _:
            raise ValueError(f"Unknown database: {db_type}")

conn = create_connection("postgres")
```

```python
# Factory with configuration
from dataclasses import dataclass

@dataclass(frozen=True)
class ConnectionConfig:
    host: str
    port: int
    database: str

def create_postgres(config: ConnectionConfig) -> PostgresConnection:
    return PostgresConnection(
        host=config.host,
        port=config.port,
        database=config.database,
    )

# Partial application for pre-configured factories
from functools import partial

production_postgres = partial(create_postgres, ConnectionConfig(
    host="prod-db.example.com",
    port=5432,
    database="app_prod",
))
```

```python
# Class as factory (callable)
class User:
    def __init__(self, name: str, role: str = "member") -> None:
        self.name = name
        self.role = role

    @classmethod
    def admin(cls, name: str) -> User:
        return cls(name, role="admin")

    @classmethod
    def from_dict(cls, data: dict) -> User:
        return cls(name=data["name"], role=data.get("role", "member"))

admin = User.admin("Alice")
user = User.from_dict({"name": "Bob"})
```

**When to use Factory:**
- Multiple ways to create an object
- Creation logic is complex
- Need to abstract concrete class choice

## Abstract Factory

Create families of related objects. Use dict of callables or module namespaces.

```python
# Dict of factories
from collections.abc import Callable
from typing import Protocol

class Button(Protocol):
    def render(self) -> str: ...

class TextInput(Protocol):
    def render(self) -> str: ...

UIFactory = dict[str, Callable[[], Button | TextInput]]

LIGHT_THEME: UIFactory = {
    "button": LightButton,
    "input": LightTextInput,
}

DARK_THEME: UIFactory = {
    "button": DarkButton,
    "input": DarkTextInput,
}

def create_ui(factory: UIFactory) -> tuple[Button, TextInput]:
    return factory["button"](), factory["input"]()
```

```python
# Module as factory namespace
# themes/light.py
class Button:
    def render(self) -> str:
        return "<button class='light'>Click</button>"

class TextInput:
    def render(self) -> str:
        return "<input class='light'/>"

# themes/dark.py
class Button:
    def render(self) -> str:
        return "<button class='dark'>Click</button>"

class TextInput:
    def render(self) -> str:
        return "<input class='dark'/>"

# Usage
import themes.light as theme
# or: import themes.dark as theme

button = theme.Button()
text_input = theme.TextInput()
```

```python
# Generic factory registry
from typing import TypeVar, Generic

T = TypeVar("T")

class Registry(Generic[T]):
    def __init__(self) -> None:
        self._factories: dict[str, Callable[..., T]] = {}

    def register(self, name: str, factory: Callable[..., T]) -> None:
        self._factories[name] = factory

    def create(self, name: str, *args, **kwargs) -> T:
        if name not in self._factories:
            raise KeyError(f"Unknown factory: {name}")
        return self._factories[name](*args, **kwargs)

# Usage
exporters: Registry[Exporter] = Registry()
exporters.register("json", JSONExporter)
exporters.register("csv", CSVExporter)
exporter = exporters.create("json", indent=2)
```

**When to use Abstract Factory:**
- Families of related objects (UI themes, database adapters)
- Swapping entire implementations (test vs production)
- Plugin systems

## Builder Pattern

Construct complex objects step by step. Use dataclasses with `replace()` or fluent methods.

```python
# Dataclass with replace() - immutable builder
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str = ""
    body: str = ""
    cc: tuple[str, ...] = ()
    attachments: tuple[Path, ...] = ()

# Build incrementally
message = EmailMessage(to="user@example.com")
message = replace(message, subject="Hello")
message = replace(message, body="Welcome to our service")
message = replace(message, cc=("manager@example.com",))
```

```python
# Fluent builder (when many optional params)
from dataclasses import dataclass, field

@dataclass
class QueryBuilder:
    _table: str = ""
    _columns: list[str] = field(default_factory=list)
    _where: list[str] = field(default_factory=list)
    _order_by: str = ""
    _limit: int | None = None

    def select(self, *columns: str) -> QueryBuilder:
        self._columns = list(columns)
        return self

    def from_table(self, table: str) -> QueryBuilder:
        self._table = table
        return self

    def where(self, condition: str) -> QueryBuilder:
        self._where.append(condition)
        return self

    def order_by(self, column: str) -> QueryBuilder:
        self._order_by = column
        return self

    def limit(self, n: int) -> QueryBuilder:
        self._limit = n
        return self

    def build(self) -> str:
        cols = ", ".join(self._columns) or "*"
        sql = f"SELECT {cols} FROM {self._table}"
        if self._where:
            sql += f" WHERE {' AND '.join(self._where)}"
        if self._order_by:
            sql += f" ORDER BY {self._order_by}"
        if self._limit:
            sql += f" LIMIT {self._limit}"
        return sql

# Fluent usage
query = (
    QueryBuilder()
    .select("id", "name", "email")
    .from_table("users")
    .where("active = true")
    .where("created_at > '2024-01-01'")
    .order_by("created_at DESC")
    .limit(100)
    .build()
)
```

```python
# Director pattern (predefined configurations)
def build_admin_query() -> str:
    return (
        QueryBuilder()
        .select("*")
        .from_table("users")
        .where("role = 'admin'")
        .build()
    )

def build_recent_users_query(days: int = 7) -> str:
    return (
        QueryBuilder()
        .select("id", "name", "created_at")
        .from_table("users")
        .where(f"created_at > NOW() - INTERVAL '{days} days'")
        .order_by("created_at DESC")
        .build()
    )
```

**When to use Builder:**
- Many optional parameters
- Object requires multiple construction steps
- Same construction process, different representations

## When NOT to Use

| Pattern | Skip When |
|---------|-----------|
| Factory | Single constructor is clear |
| Abstract Factory | Only one implementation family |
| Builder | Few required parameters, no optional ones |

## Summary Table

| Pattern | Python Idiom | Use Case |
|---------|--------------|----------|
| Factory Method | Function, `@classmethod` | Multiple creation strategies |
| Abstract Factory | Dict of callables, module namespace | Family of related objects |
| Builder | `replace()`, fluent methods | Complex object with many options |
