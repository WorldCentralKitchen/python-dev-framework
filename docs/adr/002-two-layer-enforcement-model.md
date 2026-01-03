# ADR-002: Two-Layer Enforcement Model

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-28 |
| Deciders | TBD |
| Related | [ADR-001](001-python-dev-framework-architecture.md), [ADR-003](003-configuration-strictness-levels.md) |

## Context

Code quality enforcement can occur at multiple points: edit time, save time, commit time, or CI. Need to balance fast feedback with strict gatekeeping.

## Decision

Implement **two-layer enforcement**:

### Layer 1: Claude Code Hooks (Real-time)

| Event | Trigger | Action |
|-------|---------|--------|
| PostToolUse | Edit\|Write on .py | Auto-format with ruff + black |
| PreToolUse | Bash (git commands) | Validate branch/commit patterns |

**Behavior by strictness level** (see [ADR-003](003-configuration-strictness-levels.md)):

| Level | Format | Lint errors | Type errors | Git validation |
|-------|--------|-------------|-------------|----------------|
| strict | Auto-fix | Warn | Warn | Block |
| moderate | Auto-fix | Warn | Skip | Warn |
| minimal | Auto-fix | Skip | Skip | Skip |

### Layer 2: Pre-commit (Git-level)

```yaml
hooks:
  - ruff (--exit-non-zero-on-fix)
  - black
  - mypy --strict
  - pytest --cov-fail-under=75
  - conventional-pre-commit
```

**Pre-commit always blocks** on failures regardless of plugin strictness level.

### Integration Model

| Action | Claude Hook | Pre-commit |
|--------|-------------|------------|
| Format Python | Auto-fix on save | Verify formatted |
| Lint errors | Warn (don't block) | Block on errors |
| Type errors | Warn (configurable) | Block on errors |
| Branch naming | Warn or block | N/A (push hook) |
| Commit message | Warn or block | Block on commit |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Hooks only | Misses human edits, no final gate |
| Pre-commit only | No real-time feedback, slower iteration |
| CI only | Too late, expensive to fix |
| Blocking hooks only | Too disruptive, no flexibility |

## Consequences

### Positive
- Fast feedback during Claude sessions
- Strict gate before commits
- Catches both Claude and human edits
- Configurable friction level

### Negative
- Duplicate tool runs (hook then pre-commit)
- Configuration in two places
- Potential for conflicting tool versions

### Risks

| Risk | Mitigation |
|------|------------|
| Tool version mismatch | Both layers use `uv run` from same lockfile |
| Double formatting | Pre-commit exits 0 if already formatted |
| Confusing UX | Document complementary model clearly |

## Approval Checklist

- [ ] Hook behavior documented per strictness level
- [ ] Pre-commit config tested
- [ ] Integration tested (no conflicts)
- [ ] Consumer documentation complete
