# ADR-008: Linting Rule Strategy

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-28 |
| Deciders | TBD |
| Related | [ADR-001](001-python-dev-framework-architecture.md), [ADR-004](004-prescribed-dependencies.md), [ADR-011](011-type-import-standards.md), [ADR-013](013-immutability-safety-patterns.md) |

## Context

The framework uses Ruff for linting but only enables a subset of available rules. Research into Python best practices, anti-patterns, and respected developer patterns identified additional enforcement opportunities:

| Source               | Key Patterns                                     |
| -------------------- | ------------------------------------------------ |
| Raymond Hettinger    | Idiomatic iteration, dictionary patterns         |
| FastAPI/Pydantic     | API boundaries, async discipline                 |
| Python Anti-Patterns | Mutable defaults, bare except, blocking in async |
| PEP 8                | Naming, imports, whitespace                      |

### Current State

The framework enables these Ruff rules:
```
E, W, F, I, B, C4, UP, ARG, SIM, TCH, PTH, ERA, PL, RUF
```

### Gaps Identified

| Gap | Impact |
|-----|--------|
| No security scanning | Vulnerabilities not caught early |
| No async validation | Blocking calls in async functions |
| No pytest conventions | Inconsistent test patterns |
| No performance checks | Suboptimal patterns persist |
| No secrets detection | Credentials may leak |
| No dead code detection | Unused code accumulates |

## Decision

### 1. Expand Ruff Rule Set

Add 16 rule categories via PostToolUse hooks and pre-commit:

| Category | Prefix | Purpose |
|----------|--------|---------|
| Security | S | flake8-bandit vulnerability checks |
| Async | ASYNC | Blocking calls, timeout issues |
| Logging | LOG | Proper logging patterns |
| Print | T20 | No print statements |
| Pytest | PT | Test conventions |
| Performance | PERF | Performance anti-patterns |
| Misc | PIE | Unnecessary code |
| Builtins | A | No shadowing built-ins |
| Complexity | C90 | McCabe threshold |
| Naming | N | PEP 8 naming |
| Boolean | FBT | Boolean trap |
| Raise | RSE | Exception raising |
| Return | RET | Return statements |
| Exceptions | TRY | Exception handling |
| F-strings | FLY | Modern string formatting |
| Modernization | FURB | Code updates |

### 2. Add Supplementary Tools

| Tool | Purpose | Why Not Ruff Alone |
|------|---------|-------------------|
| Dodgy | Secrets detection | Better SCM diff, AWS token coverage |
| Vulture | Dead code | Global analysis across files |

### 3. Enforcement Layers

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Claude Code Hooks (Real-time)          │
│ - PostToolUse: ruff check on Write/Edit         │
│ - PostToolUse: dodgy, vulture (optional)        │
├─────────────────────────────────────────────────┤
│ Layer 2: Pre-commit (Git Gate)                  │
│ - ruff check + ruff format                      │
│ - dodgy                                         │
│ - vulture --min-confidence 100                  │
├─────────────────────────────────────────────────┤
│ Layer 3: CI/CD                                  │
│ - Same as Layer 2 + coverage enforcement        │
└─────────────────────────────────────────────────┘
```

### 4. Future Consideration: LSP Integration

Claude Code supports LSP via `.lsp.json` configuration. Ruff provides a built-in language server (`ruff server`) that offers real-time diagnostics without hook latency.

| Approach | Latency | Setup |
|----------|---------|-------|
| PostToolUse hook | After edit completes | Hook script |
| LSP (`ruff server`) | Real-time as code is written | `.lsp.json` |

**Current recommendation**: Use hooks for consistency with existing enforcement model. Evaluate LSP integration as a future enhancement when Claude Code's LSP support matures.

```json
// Future .lsp.json (not implemented yet)
{
  "python": {
    "command": "ruff",
    "args": ["server"],
    "fileExtensions": [".py"]
  }
}
```

### 5. Extended Rules

Additional rule decisions based on team feedback:

| Rule                  | Code    | Decision             | Configuration          |
| --------------------- | ------- | -------------------- | ---------------------- |
| Named lambdas         | E731    | Allow (ignore)       | `ignore = ["E731"]`    |
| Private member access | SLF001  | Allow within package | Per-file-ignores       |
| Function length       | PLR0915 | Max 100 statements   | `max-statements = 100` |

#### E731: Lambda Assignments

**Decision:** Ignore (allow named lambdas)

Simple lambdas assigned to variables are acceptable for transform functions:

```python
# Allowed
normalize = lambda x: x.strip().lower()
get_name = lambda user: user.name

# Should use def (complex logic)
def process_item(item):
    if item.is_valid:
        return transform(item)
    return None
```

**Rationale:** Named lambdas improve readability for simple, single-expression transforms. Complex logic should use `def`.

#### SLF001: Private Member Access

**Decision:** Allow within same package via per-file-ignores

```toml
[tool.ruff.lint]
select = ["SLF"]  # Enable private member checks

[tool.ruff.lint.per-file-ignores]
# Allow private access in internal modules
"src/*/_internal/*.py" = ["SLF001"]
"src/*/tests/*.py" = ["SLF001"]
"tests/**/*.py" = ["SLF001"]
```

**Rationale:** Private member access within the same package is a valid pattern for internal implementation. Tests also need access to verify private behavior.

#### PLR0915: Function Length

**Decision:** Enforce maximum 100 statements per function

```toml
[tool.ruff.lint.pylint]
max-statements = 100
```

**Rationale:** Functions exceeding 100 statements are difficult to understand and test. This threshold catches egregious cases while allowing reasonable flexibility.

**Exceptions:** Use `# noqa: PLR0915` for legitimate cases (e.g., large switch-like dispatch functions).

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Fewer rule categories | Misses valuable checks from research |
| More categories (D, ANN) | Diminishing returns, increased noise |
| LSP-only approach | Hook model is proven, LSP is newer |

## Consequences

### Positive

- Security issues caught early (S)
- Async anti-patterns prevented (ASYNC)
- Consistent pytest style (PT)
- Performance issues flagged (PERF)
- Fast feedback via Ruff (10-100x faster than alternatives)

### Negative

- More rules = more potential false positives
- Learning curve for new categories
- May require ignore directives

### Risks

| Risk | Mitigation |
|------|------------|
| False positives | Per-file-ignores, inline noqa |
| Hook performance | Ruff is fast; Dodgy/Vulture are regex/AST-based |
| Rule conflicts | Test expanded config before rollout |

## References

- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [Python Anti-Patterns](https://docs.quantifiedcode.com/python-anti-patterns/)
- [Idiomatic Python (Hettinger)](https://github.com/JeffPaine/beautiful_idiomatic_python)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)

## Approval Checklist

- [ ] Expanded rules tested on codebase
- [ ] False positive rate acceptable
- [ ] Pre-commit hooks updated
- [ ] CLAUDE.md updated with new rules
