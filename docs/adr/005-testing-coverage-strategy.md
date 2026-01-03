# ADR-005: Testing Coverage Strategy

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-28 |
| Deciders | TBD |
| Related | [ADR-001](001-python-dev-framework-architecture.md), [ADR-003](003-configuration-strictness-levels.md), [ADR-004](004-prescribed-dependencies.md) |

## Context

Code coverage metrics can drive behavior—either toward meaningful testing or gaming numbers. Need a strategy that encourages quality tests without creating perverse incentives.

## Decision

Adopt a **75% project-wide minimum coverage threshold** with guidance on critical path testing.

### Coverage Threshold

| Threshold | Classification | Source |
|-----------|----------------|--------|
| 60% | Acceptable | Google Testing Blog[^1] |
| **75%** | Commendable | Google Testing Blog[^1] |
| 90% | Exemplary | Google Testing Blog[^1] |

[^1]: [Code Coverage Best Practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html)

**Decision: 75%** — High enough to ensure meaningful coverage, low enough to avoid test bloat.

### Enforcement

**Pre-commit hook** (blocking, per [ADR-002](002-two-layer-enforcement-model.md)):

```yaml
- repo: local
  hooks:
    - id: pytest-coverage
      name: pytest with coverage
      entry: uv run pytest --cov=src --cov-fail-under=75 --cov-report=term-missing
      language: system
      types: [python]
      pass_filenames: false
```

**pytest configuration:**

```toml
[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
fail_under = 75
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

### Critical Paths (Must Be Tested)

Regardless of overall coverage, these paths require explicit tests:

| Category | Examples |
|----------|----------|
| Authentication/Authorization | Login, token validation, permission checks |
| Payment/Financial | Transactions, calculations, refunds |
| Data Validation | Input sanitization, schema validation |
| Error Handling | Exception paths, fallback behavior |
| Security Controls | Rate limiting, input filtering |

### Test Patterns

| Pattern | Description |
|---------|-------------|
| Arrange-Act-Assert | Clear test structure |
| One assertion per test | When practical, improves failure diagnosis |
| Fixtures | Shared setup, DRY |
| Parametrize | Multiple inputs, same logic |

### What NOT to Optimize

Focus on **what's NOT covered**, not hitting a number:

| Anti-pattern | Why Avoid |
|--------------|-----------|
| Testing getters/setters | Low value, inflates numbers |
| Testing framework code | Already tested upstream |
| 100% coverage goal | Diminishing returns, test bloat |
| Coverage-only metrics | Quality matters more than quantity |

### Excluded from Coverage

```toml
exclude_lines = [
    "pragma: no cover",      # Explicit exclusion
    "if TYPE_CHECKING:",     # Type hints only
    "raise NotImplementedError",  # Abstract methods
]
```

### Plugin Testing Strategy

The plugin itself uses:

| Layer | Scope | Tools |
|-------|-------|-------|
| Unit tests | Config loader, pattern matching | pytest |
| E2E tests | Full hook execution | Claude Code / Agent SDK |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| No threshold | No enforcement, coverage drift |
| 90% threshold | Encourages low-value tests, high maintenance |
| 60% threshold | Too permissive, misses important code |
| File-level thresholds | Too granular, administrative overhead |
| CI-only enforcement | Feedback too late, expensive to fix |

## Consequences

### Positive
- Consistent baseline across projects
- Focus on meaningful coverage
- Fast feedback via pre-commit
- Critical paths explicitly identified

### Negative
- May block commits during rapid prototyping
- Threshold is somewhat arbitrary
- Doesn't guarantee test quality

### Risks

| Risk | Mitigation |
|------|------------|
| Gaming the metric | Review focuses on critical paths, not percentage |
| Blocking urgent fixes | `--no-verify` escape hatch (logged) |
| False sense of security | CLAUDE.md emphasizes quality over quantity |

## Approval Checklist

- [ ] 75% threshold validated on sample projects
- [ ] Critical path guidance documented
- [ ] Pre-commit configuration tested
- [ ] Exclusion patterns appropriate
