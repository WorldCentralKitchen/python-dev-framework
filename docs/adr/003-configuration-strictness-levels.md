# ADR-003: Configuration and Strictness Levels

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-28 |
| Deciders | TBD |
| Related | [ADR-001](001-python-dev-framework-architecture.md), [ADR-002](002-two-layer-enforcement-model.md), [ADR-005](005-testing-coverage-strategy.md) |

## Context

Different projects have different quality requirements. New projects need flexibility during early development; mature projects need strict enforcement. A one-size-fits-all approach creates adoption friction.

## Decision

Implement **three strictness levels** configurable per-project:

### Strictness Matrix

| Capability | strict | moderate | minimal |
|------------|--------|----------|---------|
| Type hints | mypy --strict, block on errors | mypy basic, warn only | Disabled |
| Linting | All rules, no ignores | Core rules (E,W,F,I,B) | Format only (black) |
| Commit validation | Required, blocks invalid | Required, warns only | Optional |
| Branch validation | Required, blocks invalid | Required, warns only | Optional |
| Coverage threshold | 75% ([ADR-005](005-testing-coverage-strategy.md)) | 75% ([ADR-005](005-testing-coverage-strategy.md)) | None |

### Configuration Location

Consumer projects configure via `.claude/settings.json`:

```json
{
  "plugins": {
    "python-dev-framework": {
      "level": "strict",
      "branch_types": ["feature", "bugfix", "hotfix", "refactor", "docs", "test", "chore"],
      "commit_types": ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"]
    }
  }
}
```

### Default Values

| Setting | Default |
|---------|---------|
| level | strict |
| branch_types | feature, bugfix, hotfix, refactor, docs, test, chore |
| commit_types | feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert |

### Config Reading

Hooks read from `$CLAUDE_PROJECT_DIR/.claude/settings.json`:

```python
@dataclass
class PluginConfig:
    level: str = "strict"
    branch_types: list[str] = field(default_factory=lambda: [...])
    commit_types: list[str] = field(default_factory=lambda: [...])
```

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Single strictness | No flexibility, adoption friction |
| Per-rule configuration | Too complex, overwhelming options |
| Environment variables | Not persistent, hard to track |
| pyproject.toml | Not Claude Code native, mixing concerns |

## Consequences

### Positive
- Gradual adoption path (minimal → moderate → strict)
- Project-specific tuning
- Clear expectations per level
- Native Claude Code configuration

### Negative
- Three behaviors to document/test
- Users must understand level differences
- Potential for "stuck on minimal"

### Risks

| Risk | Mitigation |
|------|------------|
| Config not found | Default to strict (fail closed) |
| Invalid level | Log warning, default to strict |
| Missing settings.json | Use all defaults |

## Approval Checklist

- [ ] All three levels fully documented
- [ ] Default behavior tested
- [ ] Config reading error handling tested
- [ ] Consumer documentation includes level selection guidance
