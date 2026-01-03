# ADR-006: End-to-End Testing Strategy

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-28 |
| Deciders | TBD |
| Related | [ADR-002](002-two-layer-enforcement-model.md), [ADR-005](005-testing-coverage-strategy.md) |

## Context

Unit tests verify hook logic in isolation but cannot confirm hooks work correctly when triggered by Claude Code. Need a strategy to test the full integration: Claude CLI → hook execution → expected behavior.

## Decision

Implement **E2E tests using `claude -p` CLI with subprocess**, isolated temp directories per test, and `--plugin-dir` for plugin loading.

### Architecture

```
tests/
├── conftest.py              # Skip E2E if Claude CLI unavailable
├── test_*.py                # Unit tests (existing)
└── e2e/
    ├── conftest.py          # E2E fixtures
    ├── helpers.py           # CLI wrapper functions
    ├── test_format_hook.py  # PostToolUse tests
    └── test_validate_hook.py # PreToolUse tests
```

### Key Mechanisms

| Mechanism | Implementation |
|-----------|----------------|
| Plugin loading | `--plugin-dir` flag loads plugin from source |
| Isolation | Fresh `tmp_path` per test with git init |
| Non-interactive | `--dangerously-skip-permissions` flag |
| Structured output | `--output-format json` for result parsing |
| CI safety | Skip marker when Claude CLI not in PATH |

### CLI Invocation Pattern

```python
def run_claude(prompt: str, *, project_dir: Path) -> ClaudeResult:
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--plugin-dir", str(PLUGIN_ROOT),
        "--dangerously-skip-permissions",
        prompt
    ]
    result = subprocess.run(cmd, cwd=project_dir, ...)
    return ClaudeResult(returncode, stdout, stderr, output_json)
```

### Test Fixtures

| Fixture | Purpose |
|---------|---------|
| `e2e_project(tmp_path)` | Creates temp dir with `.claude/`, `pyproject.toml`, git init |
| `strict_settings` | Configures `level: strict` in settings.json |
| `moderate_settings` | Configures `level: moderate` in settings.json |
| `minimal_settings` | Configures `level: minimal` in settings.json |

### Test Coverage Matrix

| Hook | Scenario | Strictness | Expected |
|------|----------|------------|----------|
| PostToolUse | Write Python file | strict | Formatted (ruff + black) |
| PostToolUse | Write Python file | minimal | Formatted (black only) |
| PostToolUse | Write non-Python | any | Unchanged |
| PreToolUse | Valid branch | strict | Allowed |
| PreToolUse | Invalid branch | strict | Blocked |
| PreToolUse | Invalid branch | moderate | Warned, allowed |
| PreToolUse | Valid commit | strict | Allowed |
| PreToolUse | Invalid commit | strict | Blocked |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Claude Agent SDK | Requires API key management, more complex setup |
| Hook-level simulation only | Doesn't test real CLI integration |
| Manual testing only | Not reproducible, no CI integration |
| Docker containers | Overhead for simple subprocess tests |

## Consequences

### Positive
- Tests actual plugin behavior in Claude Code
- Reproducible via pytest
- Can run in CI with Claude CLI installed
- Isolated tests don't affect each other

### Negative
- E2E tests invoke LLM (cost, latency)
- Requires Claude CLI installed
- Tests may be flaky due to LLM non-determinism
- Cannot run in environments without API access

### Risks

| Risk | Mitigation |
|------|------------|
| LLM cost | Run E2E tests on-demand or main branch only |
| Flaky tests | Focus assertions on hook behavior, not exact output |
| CI complexity | Skip marker when CLI unavailable |
| Timeout | 120s default timeout per test |

## Approval Checklist

- [ ] E2E test framework reviewed
- [ ] CI workflow tested with Claude CLI
- [ ] Cost impact assessed
- [ ] Flakiness monitoring in place
