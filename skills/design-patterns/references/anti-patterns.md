# Python Anti-Patterns

Common design mistakes and their Pythonic alternatives.

## Singleton Abuse

Python modules are already singletons. Don't create singleton classes.

```python
# BAD: Unnecessary singleton class
class ConfigSingleton:
    _instance: ConfigSingleton | None = None

    def __new__(cls) -> ConfigSingleton:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.settings = self._load_settings()
```

```python
# GOOD: Module-level instance
# config.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    database_url: str
    debug: bool

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            database_url=os.environ["DATABASE_URL"],
            debug=os.environ.get("DEBUG", "false").lower() == "true",
        )

# Module-level instance (lazy initialization)
_config: Config | None = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
```

**Why modules are singletons:** Python caches imported modules in `sys.modules`. The first import creates the module; subsequent imports return the cached instance.

## Inheritance Overuse

Deep inheritance hierarchies create tight coupling. Prefer composition.

```python
# BAD: Inheritance hierarchy
class Animal:
    def eat(self) -> None: ...

class Mammal(Animal):
    def give_birth(self) -> None: ...

class Swimmer:
    def swim(self) -> None: ...

class Dolphin(Mammal, Swimmer):  # Multiple inheritance issues
    pass

class FlyingFish(Animal, Swimmer):  # Doesn't fit hierarchy
    def fly(self) -> None: ...  # But fish can't fly?
```

```python
# GOOD: Composition with protocols
from typing import Protocol

class CanSwim(Protocol):
    def swim(self) -> None: ...

class CanFly(Protocol):
    def fly(self) -> None: ...

@dataclass
class Dolphin:
    name: str

    def swim(self) -> None:
        log.info("swimming", name=self.name)

    def eat(self) -> None:
        log.info("eating", name=self.name)

def ocean_race(swimmers: list[CanSwim]) -> None:
    for swimmer in swimmers:
        swimmer.swim()  # Works with any CanSwim
```

**Rule of thumb:** Inherit for "is-a" relationships only when behavior is truly shared. Use composition for "has-a" or "can-do" relationships.

## Java-Style Getters/Setters

Python uses `@property` for controlled attribute access.

```python
# BAD: Java-style boilerplate
class User:
    def __init__(self, name: str) -> None:
        self._name = name

    def get_name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        self._name = name

# Usage
user.set_name("Alice")
print(user.get_name())
```

```python
# GOOD: Direct attribute access (start here)
class User:
    def __init__(self, name: str) -> None:
        self.name = name

# Usage
user.name = "Alice"
print(user.name)
```

```python
# GOOD: @property when validation needed (add later)
class User:
    def __init__(self, name: str) -> None:
        self.name = name  # Uses setter

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value.strip():
            raise ValueError("Name cannot be empty")
        self._name = value.strip()
```

**Key insight:** Start with simple attributes. Add `@property` only when you need validation or computed values. The interface remains unchanged.

## God Object

A class that knows too much or does too much violates SRP.

```python
# BAD: God object
class Application:
    def __init__(self) -> None:
        self.db = Database()
        self.cache = Cache()
        self.mailer = Mailer()
        self.logger = Logger()
        self.config = Config()

    def create_user(self, data: dict) -> User: ...
    def send_email(self, to: str, body: str) -> None: ...
    def process_payment(self, amount: float) -> None: ...
    def generate_report(self) -> str: ...
    def backup_database(self) -> None: ...
    def clear_cache(self) -> None: ...
    def update_config(self, key: str, value: str) -> None: ...
```

```python
# GOOD: Focused classes
class UserService:
    def __init__(self, db: Database, mailer: Mailer) -> None:
        self.db = db
        self.mailer = mailer

    def create(self, data: dict) -> User: ...
    def notify(self, user: User, message: str) -> None: ...

class PaymentService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def process(self, amount: float) -> Receipt: ...

# Composition at the application level
class Application:
    def __init__(self) -> None:
        self.users = UserService(db, mailer)
        self.payments = PaymentService(db)
```

**Signs of a God Object:**
- More than ~7-10 methods unrelated to each other
- Dependencies on many other modules
- Hard to test in isolation
- Changes frequently for unrelated reasons

## Method Could Be a Function

Methods that don't use `self` should be module-level functions.

```python
# BAD: Method doesn't use self
class MathUtils:
    def add(self, a: int, b: int) -> int:
        return a + b  # self is unused

    def multiply(self, a: int, b: int) -> int:
        return a * b  # self is unused

# Awkward usage
utils = MathUtils()
result = utils.add(1, 2)
```

```python
# GOOD: Module-level functions
# math_utils.py
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

# Clean usage
from math_utils import add, multiply
result = add(1, 2)
```

**Exception:** `@staticmethod` is acceptable for namespace organization:

```python
class DateUtils:
    @staticmethod
    def parse(date_str: str) -> date: ...

    @staticmethod
    def format(d: date) -> str: ...
```

## Premature Pattern Application

Adding patterns for hypothetical future requirements.

```python
# BAD: Factory for single implementation
class UserRepositoryFactory:
    def create(self) -> UserRepository:
        return PostgresUserRepository()  # Only one implementation

# BAD: Strategy for single algorithm
class SortStrategy(Protocol):
    def sort(self, items: list) -> list: ...

class QuickSortStrategy:
    def sort(self, items: list) -> list:
        return sorted(items)  # Python's sort is fine

class Sorter:
    def __init__(self, strategy: SortStrategy) -> None:
        self.strategy = strategy
```

```python
# GOOD: Direct, simple code
def get_user_repository() -> PostgresUserRepository:
    return PostgresUserRepository()

def sort_items(items: list) -> list:
    return sorted(items)
```

**YAGNI (You Aren't Gonna Need It):** Add patterns when you have multiple implementations, not before.

## Summary Table

| Anti-Pattern | Problem | Pythonic Alternative |
|--------------|---------|---------------------|
| Singleton class | Complexity, testing difficulty | Module-level instance |
| Deep inheritance | Coupling, diamond problem | Composition + Protocol |
| Java getters/setters | Boilerplate | Direct attributes, `@property` |
| God Object | SRP violation, untestable | Focused classes, composition |
| Unused self | Unnecessary class | Module-level function |
| Premature patterns | Over-engineering | Simple code, refactor when needed |

## Detection Checklist

- [ ] Does the class have "Manager", "Handler", "Utils" in its name?
- [ ] Does the class have more than 10 methods?
- [ ] Is there a singleton pattern that could be a module?
- [ ] Are there getters/setters without validation logic?
- [ ] Are there methods that don't reference `self`?
- [ ] Is there a pattern with only one implementation?
