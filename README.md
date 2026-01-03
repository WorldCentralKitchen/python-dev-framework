# Python Development Framework Plugin

Guardrails for LLM-assisted Python development with Claude Code.

This plugin guides Claude toward production-quality code by enforcing type safety, formatting standards, and git conventions in real-time. When Claude writes code that doesn't meet standards, it gets immediate feedback and can self-correct.

## Features

- **Real-time diagnostics**: LSP integration with Ruff for instant feedback
- **Type enforcement**: mypy --strict catches missing annotations as Claude codes
- **Auto-formatting**: ruff + black applied on every file write
- **Git conventions**: Branch names and commit messages validated before execution
- **Python version aware**: Detects target Python version and adjusts rules accordingly
- **`__future__` enforcement**: Requires `from __future__ import annotations` in strict mode
- **Configurable strictness**: strict (block - default), moderate (warn), or minimal (format only)

## Installation

### Prerequisites

- [Claude Code CLI](https://claude.ai/code) installed
- [GitHub CLI](https://cli.github.com/) installed
- Access to WorldCentralKitchen/wck-claude-plugins (private repo)

### Setup GitHub CLI

```bash
# Install (macOS)
brew install gh

# Authenticate
gh auth login
```

### Install Plugin

Run from your terminal (not inside Claude Code):

```bash
# Add marketplace (one-time)
claude plugin marketplace add "https://oauth:$(gh auth token)@github.com/WorldCentralKitchen/wck-claude-plugins.git"

# Install plugin
claude plugin install python-dev-framework@WorldCentralKitchen
```

To install a specific version:

```bash
claude plugin marketplace add "https://oauth:$(gh auth token)@github.com/WorldCentralKitchen/wck-claude-plugins.git#v0.1.0"
claude plugin install python-dev-framework@WorldCentralKitchen
```

### Verify Installation

```bash
claude plugin list
```

> **Note:** Claude Code doesn't support private repo auth natively ([#9756](https://github.com/anthropics/claude-code/issues/9756)). The token-in-URL workaround above uses `gh auth token` to inject your GitHub credentials.

## Configuration

Optional: Create `.claude/settings.json` to customize:

```json
{
  "plugins": {
    "python-dev-framework": {
      "level": "strict"
    }
  }
}
```

| Level | Formatting | Type Checking | Git Validation |
|-------|------------|---------------|----------------|
| strict | ruff + black | mypy --strict | Block invalid |
| moderate | ruff + black | Disabled | Warn only |
| minimal | black only | Disabled | Disabled |

### Python Version Detection

The plugin automatically detects your target Python version from `pyproject.toml`:

1. `tool.ruff.target-version` (e.g., `"py39"`) — highest priority
2. `project.requires-python` (e.g., `">=3.9"`) — parsed to extract version
3. Default: `py312`

Version-specific behavior:

| Version | `__future__` Check | FA Rules | UP036 Ignore |
|---------|-------------------|----------|--------------|
| py39 | ✓ (strict) | ✓ | ✓ (no match) |
| py310 | ✓ (strict) | ✓ | — |
| py311+ | ✓ (strict) | — | — |

- **FA rules**: `flake8-future-annotations` catches missing `__future__` imports
- **UP036**: Ignored for py39 since `match` statements aren't available

## Consumer Setup

Projects using this plugin need:

1. `pyproject.toml` with tool configurations
2. `.pre-commit-config.yaml` for git hooks
3. Dev dependencies: pytest, mypy, ruff, black, pre-commit
4. `from __future__ import annotations` at the top of all Python files (strict mode)

### Required: `__future__` Annotations

In strict mode, all Python files must include:

```python
from __future__ import annotations
```

This enables modern type syntax (`str | None`, `list[int]`) across all supported Python versions (3.9+). The plugin blocks writes that omit this import.

### Type Checking Configuration

In strict mode, mypy runs on every Python file after Write/Edit. The plugin passes `--python-version` based on your detected target version.

Configure exclusions in your `pyproject.toml`:

```toml
[project]
requires-python = ">=3.9"

[tool.ruff]
target-version = "py39"  # Must match requires-python

[tool.mypy]
strict = true
python_version = "3.9"   # Must match requires-python

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

The plugin defers to your project's mypy configuration.

### Ruff Rules

The plugin enables comprehensive linting via Ruff:

| Category | Prefix | Purpose |
|----------|--------|---------|
| Pycodestyle | E, W | PEP 8 style |
| Pyflakes | F | Logic errors, unused imports |
| isort | I | Import sorting |
| Bugbear | B | Common bugs, mutable defaults |
| Comprehensions | C4 | List/dict comprehension style |
| Pyupgrade | UP | Python version upgrades |
| Unused args | ARG | Unused function arguments |
| Simplify | SIM | Code simplification |
| flake8-print | T | Bans `print()` in src/ (use structlog) |
| flake8-future | FA | `__future__` annotations (py39/py310) |
| Type checking | TCH | TYPE_CHECKING block usage |
| Pathlib | PTH | pathlib over os.path |
| Eradicate | ERA | Commented-out code |
| Pylint | PL | Additional checks |
| Ruff | RUF | Ruff-specific rules |

See [ADR-008](docs/adr/008-linting-rule-strategy.md) for expanded rules including security (S), async (ASYNC), and pytest (PT) categories.

### Print Ban (T201)

In strict mode, `print()` is banned in `src/` directories via Ruff T201. Use structlog instead:

```python
import structlog
log = structlog.get_logger()
log.info("event_name", user_id=123)
```

Exempt locations (via per-file-ignores):
- `tests/**/*.py` — print allowed in tests
- `python-dev-framework/hooks/scripts/*.py` — hooks use print for stdout protocol

See [TDD-002](docs/tdd/002-gcp-logging-integration.md) for structlog configuration patterns.

### Type Import Enforcement

The plugin auto-fixes deprecated type imports via Ruff pyupgrade (UP) rules:

| Before | After | Rule |
|--------|-------|------|
| `List[str]` | `list[str]` | UP006 |
| `Dict[str, int]` | `dict[str, int]` | UP006 |
| `Union[str, int]` | `str \| int` | UP007 |
| `Optional[str]` | `str \| None` | UP007 |
| `typing.Callable` | `collections.abc.Callable` | UP035 |

Behavior by strictness level:

| Level | UP Rules | TCH Rules |
|-------|----------|-----------|
| strict | Fix + Check | Fix + Check |
| moderate | Fix only | Disabled |
| minimal | Disabled | Disabled |

See [TDD-004](docs/tdd/004-type-import-patterns.md) for implementation details and [ADR-011](docs/adr/011-type-import-standards.md) for rationale.

### Directory Layout & Private Access

The plugin enforces private attribute access via Ruff SLF001 (flake8-self):

| Pattern | Enforcement | Rule |
|---------|-------------|------|
| `obj._private_attr` | Blocked | SLF001 |
| `obj._private_method()` | Blocked | SLF001 |
| `from pkg._internal import x` | Guidance only | — |

**Note:** SLF001 catches attribute/method access on objects, not module imports.
The `_internal/` naming convention is documented guidance.

Exempt locations (via per-file-ignores):
- `tests/**/*.py` — Tests can access private members
- `src/*/_internal/*.py` — Internal modules can access each other

Behavior by strictness level:

| Level | SLF001 |
|-------|--------|
| strict | Block violations |
| moderate | Disabled |
| minimal | Disabled |

See [TDD-005](docs/tdd/005-directory-layout-templates.md) for templates and [ADR-012](docs/adr/012-source-directory-layout.md) for rationale.

### Immutability Pattern Enforcement

The plugin enforces immutability patterns via Ruff rules:

| Rule | Pattern | Action |
|------|---------|--------|
| B006 | Mutable argument defaults `def f(x=[])` | Auto-fix |
| B039 | Mutable contextvar defaults | Block |
| RUF008 | Mutable defaults in `@dataclass` | Block |
| RUF012 | Mutable class attribute defaults | Block |

Additionally, mypy catches `Sequence[str]` footguns via `useful-types`:

```python
from useful_types import SequenceNotStr

def process(tags: SequenceNotStr[str]) -> None:
    pass

process("hello")  # Type error! str is not SequenceNotStr
```

Behavior by strictness level:

| Level | B006/B039/RUF008/RUF012 | mypy (SequenceNotStr) |
|-------|-------------------------|----------------------|
| strict | Block | Block |
| moderate | Fix + Warn | Skip |
| minimal | Skip | Skip |

See [TDD-006](docs/tdd/006-immutability-patterns.md) for implementation details and [ADR-013](docs/adr/013-immutability-safety-patterns.md) for rationale.

See [TDD-001](docs/tdd/001-plugin-implementation.md) for complete templates.

---

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) for Python package management
- [Claude Code CLI](https://claude.ai/code) installed
- [ruff](https://docs.astral.sh/ruff/) globally installed for LSP diagnostics (`brew install ruff`)

### Install Dependencies

```bash
uv sync
```

### Run Tests

```bash
# Unit tests only
uv run pytest tests/test_*.py

# E2E tests (requires Claude CLI + API key)
uv run pytest -m e2e

# All tests
uv run pytest
```

### Dogfooding

This plugin can be loaded into its own development environment for real-world testing.

```bash
claude --plugin-dir python-dev-framework
```

This enables:
- **LSP diagnostics**: Real-time linting feedback from Ruff
- **PostToolUse hook**: Auto-formats Python files on Write/Edit
- **PreToolUse hook**: Validates git branch names and commit messages

#### Escape Hatches

| Problem               | Solution                              |
| --------------------- | ------------------------------------- |
| Hook blocks your work | Restart Claude without `--plugin-dir` |
| Can't commit          | `git commit --no-verify`              |
| Need to debug         | Run hook script manually              |

### Repository Structure
```
wck-claude-plugins/                  # Marketplace repository
├── .claude-plugin/
│   └── marketplace.json             # Marketplace catalog
└── python-dev-framework/            # Plugin directory
    ├── .claude-plugin/
    │   └── plugin.json              # Plugin manifest
    ├── .lsp.json                    # LSP server configuration
    ├── hooks/
    │   ├── hooks.json               # Hook definitions
    │   └── scripts/
    │       ├── config.py            # Shared configuration loader
    │       ├── format_python.py     # PostToolUse: formats .py files
    │       └── validate_git.py      # PreToolUse: validates git commands
    └── skills/
        └── python-standards/        # Python standards skill
            └── SKILL.md
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [CLAUDE.md](CLAUDE.md) | Claude Code project instructions |
| [Architecture Decision Records](docs/adr/README.md) | Design decisions and rationale (ADR-001 through ADR-013) |

## License

MIT
