# ADR-015: Protected Branch Push Validation

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2026-01-02 |
| Deciders | TBD |
| Related | [ADR-002](002-two-layer-enforcement-model.md), [ADR-003](003-configuration-strictness-levels.md) |

## Context

LLM agents (Claude) can inadvertently push directly to protected branches (main/master), bypassing PR workflows. This happens when chaining commands like:

```bash
git add . && git commit -m "fix" && git push origin main
```

GitHub branch protection doesn't help because the agent often has admin access or push protection is not configured.

## Decision

Extend the PreToolUse git validation hook to block `git push` commands targeting main/master branches.

### Detection Strategy

| Pattern | Example | Action |
|---------|---------|--------|
| Explicit branch | `git push origin main` | Block |
| With flags | `git push -u origin main` | Block |
| Force push | `git push --force origin master` | Block |
| Bare push on main | `git push` (current branch is main) | Block |
| Chained commands | `cmd && git push origin main` | Block |
| Feature branch | `git push origin feature/foo` | Allow |
| Tag push | `git push origin v1.0.0` | Allow |

### Strictness Behavior

Per [ADR-003](003-configuration-strictness-levels.md):

| Level | Behavior |
|-------|----------|
| strict | Block with error message |
| moderate | Warn to stderr, allow push |
| minimal | Skip validation |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Rely on GitHub branch protection | Agent may have admin access |
| Block all pushes | Too restrictive, breaks feature branch workflow |
| Separate hook | Adds complexity, same trigger (Bash) |

## Consequences

### Positive

- Enforces PR workflow for protected branches
- Catches chained commands
- Consistent with existing validation pattern

### Negative

- Adds subprocess call to check current branch for bare `git push`
- Slightly longer hook execution (~10ms)

## Approval Checklist

- [ ] Hook implementation tested with edge cases
- [ ] Unit tests added
- [ ] E2E test added
- [ ] README updated
