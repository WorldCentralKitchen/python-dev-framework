# Python Development Framework Standards

## Enforced Rules

These standards are enforced by hooks and pre-commit:

| Rule | Enforcement |
|------|-------------|
| Type hints on all functions | mypy --strict |
| Code formatting | black + ruff |
| No print() in src/ | Ruff T201 (use structlog) |
| Conventional commits | type(scope): description |
| Branch naming | type/description |
| Test coverage | 75% minimum |

## Best Practices

### Code Style
- Prefer composition over inheritance
- Use `pathlib` over `os.path`
- Use dataclasses for simple data containers
- Use Pydantic only at API boundaries

### Logging

Use structlog for structured logging. See [ADR-004](docs/adr/004-prescribed-dependencies.md) and [TDD-002](docs/tdd/002-gcp-logging-integration.md).

| Requirement | Details |
|-------------|---------|
| Library | structlog>=24.1 |
| Enforcement | Ruff T201 bans `print()` in src/ |
| Format | JSON in production, console in development |
| Security | Filter sensitive fields (password, token, secret, api_key) |
| Exempt | `tests/`, `hooks/scripts/` |

```python
import structlog
log = structlog.get_logger()
log.info("event_name", user_id=123)
```

### Documentation
- Google-style docstrings for public APIs
- No docstrings for private/internal functions
- Type hints serve as primary documentation

### Git Workflow
- Branch types: feature/, bugfix/, hotfix/, refactor/, docs/, test/, chore/
- Commit types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
- Keep commits atomic and focused

## Strictness Levels

Configure in `.claude/settings.json`:

```json
{
  "plugins": {
    "python-dev-framework": {
      "level": "strict"
    }
  }
}
```

| Level | Type Checking | Linting | Git Validation |
|-------|---------------|---------|----------------|
| strict | Block on errors | All rules | Block invalid |
| moderate | Warn only | Core rules | Warn only |
| minimal | Disabled | Format only | Optional |

## Development & Testing

### Running Tests

```bash
# Unit tests only (fast, no Claude CLI needed)
uv run pytest tests/test_*.py

# E2E tests only (requires Claude CLI + API key)
uv run pytest -m e2e

# All tests
uv run pytest
```

### E2E Testing Framework

E2E tests invoke `claude -p` CLI with subprocess to test hooks in real conditions:

| Mechanism | Implementation |
|-----------|----------------|
| Plugin loading | `--plugin-dir` loads plugin from source |
| Isolation | Fresh temp directory per test with git init |
| Non-interactive | `--dangerously-skip-permissions` flag |
| Structured output | `--output-format json` for result parsing |
| CI safety | Skip marker when Claude CLI not in PATH |

Test structure:
```
tests/e2e/
├── conftest.py          # Fixtures: e2e_project, strict/moderate/minimal_settings
├── helpers.py           # run_claude(), write_file_via_claude(), run_git_via_claude()
├── test_format_hook.py  # PostToolUse formatting tests
└── test_validate_hook.py # PreToolUse git validation tests
```

See [ADR-006](docs/adr/006-e2e-testing-strategy.md) for design rationale.

## Python Version Support

Supports Python 3.9-3.13 (default: 3.12+). See [ADR-010](docs/adr/010-python-version-compatibility.md) and [TDD-003](docs/tdd/003-python-version-patterns.md).

**Required in all modules (enforced by hook in strict mode):**
```python
from __future__ import annotations
```

Version is auto-detected from `pyproject.toml`:
1. `tool.ruff.target-version` (priority)
2. `project.requires-python`
3. Default: `py312`

| Python | typing_extensions | Hook Adjustments |
|--------|-------------------|------------------|
| 3.9 | Required | +FA rules, ignore UP036 |
| 3.10 | Required | +FA rules |
| 3.11 | Optional | — |
| 3.12+ | Not needed | — |

## Type Import Standards

See [ADR-011](docs/adr/011-type-import-standards.md) and [TDD-004](docs/tdd/004-type-import-patterns.md).

| Category | Import From |
|----------|-------------|
| Protocols/ABCs | `collections.abc` |
| Container generics | Built-in (`list`, `dict`) |
| Special forms | `typing` |

**Avoid:** `typing.List`, `typing.Dict`, `typing.Union` (use `list`, `dict`, `X | Y`)

## Directory Layout

See [ADR-012](docs/adr/012-source-directory-layout.md) and [TDD-005](docs/tdd/005-directory-layout-templates.md).

| Directory | Contents |
|-----------|----------|
| `types/` | Type definitions; `_internal.py` for private |
| `models/` | Dataclasses (domain), Pydantic (API only in `api.py`) |
| `_internal/` | Private utilities; never import externally |

### Private Access (SLF001)

Ruff SLF001 enforces private attribute access restrictions in strict mode:

| Pattern | Enforcement |
|---------|-------------|
| `obj._private_attr` | **Blocked** (SLF001) |
| `obj._private_method()` | **Blocked** (SLF001) |
| `from pkg._internal import x` | Guidance only |

**Note:** SLF001 catches attribute/method access on objects, not module imports.
The `_internal/` naming convention is documented guidance only.

**Exempt locations** (via per-file-ignores):
- `tests/**/*.py` — Tests may access private members
- `src/*/_internal/*.py` — Internal modules may access each other

## Immutability Patterns

See [ADR-013](docs/adr/013-immutability-safety-patterns.md).

| Prefer | Over | Why |
|--------|------|-----|
| `tuple(items)` | `list.append()` loop | Immutable result |
| `@dataclass(frozen=True)` | `@dataclass` | Immutable objects |
| `NamedTuple` | `dataclass` (simple records) | Immutable by default |
| `SequenceNotStr[str]` | `Sequence[str]` | Prevents str-as-sequence bug |
| `frozenset()` | `set()` | Immutable sets |
| `Mapping[K, V]` | `dict[K, V]` (return type) | Read-only contract |

**Enforced by Ruff:** B006 (mutable defaults), B039, RUF012

## Project Context

[Consumer projects should add project-specific context here]
