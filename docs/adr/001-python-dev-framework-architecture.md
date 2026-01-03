# ADR-001: Python Development Framework Architecture

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-28 |
| Deciders | TBD |
| Related | [ADR-002](002-two-layer-enforcement-model.md), [ADR-003](003-configuration-strictness-levels.md), [ADR-004](004-prescribed-dependencies.md), [ADR-005](005-testing-coverage-strategy.md) |

## Context

Claude Code lacks standardized Python development enforcement. Teams need consistent linting, formatting, type checking, and git workflow validation across projects. Manual enforcement is error-prone and inconsistent.

## Decision

Implement a **Claude Code Plugin** that enforces Python development standards through:

| Component       | Technology                                                      | Rationale                                    |
| --------------- | --------------------------------------------------------------- | -------------------------------------------- |
| Package manager | [uv](https://github.com/astral-sh/uv) + uv.lock                 | Fast, deterministic, modern                  |
| Linting         | [Ruff](https://github.com/astral-sh/ruff)                       | Fast, comprehensive, replaces multiple tools |
| Formatting      | [Black](https://github.com/psf/black)                           | Industry standard, zero config               |
| Type checking   | [mypy](https://github.com/python/mypy) --strict                 | Full type safety                             |
| Python version  | 3.12+                                                           | Modern features, typing improvements         |
| Git workflow    | [Conventional Commits](https://conventionalcommits.org)         | Semantic versioning, changelog automation    |
| Hook SDK        | [cchooks](https://github.com/GowayLee/cchooks)                  | Typed contexts, clean API                    |
| Validation      | [Pydantic](https://github.com/pydantic/pydantic) (at API boundaries) | Prescribed for consumer projects        |
| Logging         | [structlog](https://github.com/hynek/structlog) (consumers)     | Structured, JSON-compatible                  |

### Plugin Structure

```
python-dev-framework/
├── .claude-plugin/
│   └── plugin.json          # Manifest
├── hooks/
│   ├── hooks.json           # Event configuration
│   └── scripts/
│       ├── format_python.py # PostToolUse
│       └── validate_git.py  # PreToolUse
├── skills/
│   └── python-standards/
│       └── SKILL.md
└── CLAUDE.md
```

## Alternatives Considered

| Alternative       | Rejected Because                                      |
| ----------------- | ----------------------------------------------------- |
| Project templates | One-time setup, no ongoing enforcement                |
| CLAUDE.md only    | Guidance without enforcement                          |
| Pre-commit only   | No real-time feedback for LLMs during Claude sessions |
| Flake8 + isort    | Slower, requires multiple tools; Ruff consolidates    |

## Consequences

### Positive
- Consistent enforcement across all adopting projects
- Real-time feedback during development
- Reduced code review friction
- Type safety catches bugs at edit time

### Negative
- Learning curve for teams new to strict typing
- Plugin dependency creates coupling
- Initial setup overhead for existing projects

### Error Handling: Fail Closed

Hooks block operations when dependencies are missing. This ensures enforcement cannot be bypassed accidentally.

```python
if not shutil.which("uv"):
    ctx.output.deny(reason="uv not found", system_message="Install uv: ...")
```

### Risks

| Risk | Mitigation |
|------|------------|
| Tool version drift | Pin versions in plugin, test before releases |
| Performance impact | Hooks run only on .py files, async where possible |
| False positives | Configurable strictness levels ([ADR-003](003-configuration-strictness-levels.md)) |
| Missing dependencies | Fail closed with actionable error messages |

## Approval Checklist

- [ ] Architecture review completed
- [ ] Security review of hook scripts
- [ ] Consumer project pilot tested
- [ ] Documentation complete
