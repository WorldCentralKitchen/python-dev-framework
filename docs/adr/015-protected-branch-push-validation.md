# ADR-015: Protected Branch Enforcement

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-01-02 |
| Deciders | TBD |
| Related | [ADR-002](002-two-layer-enforcement-model.md), [ADR-003](003-configuration-strictness-levels.md) |

## Context

LLM agents (Claude) can inadvertently bypass PR workflows by:

1. Pushing directly to protected branches (main/master):
   ```bash
   git add . && git commit -m "fix" && git push origin main
   ```

2. Merging PRs via CLI without human review:
   ```bash
   gh pr merge 123 --squash
   ```

GitHub branch protection doesn't help because the agent often has admin access or push protection is not configured.

## Decision

Extend the PreToolUse git validation hook to block:
- `git push` commands targeting main/master branches
- `gh pr merge` commands (all PR merges require human approval)

### Detection Strategy

#### Push Validation

| Pattern | Example | Action |
|---------|---------|--------|
| Explicit branch | `git push origin main` | Block |
| With flags | `git push -u origin main` | Block |
| Force push | `git push --force origin master` | Block |
| Bare push on main | `git push` (current branch is main) | Block |
| Chained commands | `cmd && git push origin main` | Block |
| Feature branch | `git push origin feature/foo` | Allow |
| Tag push | `git push origin v1.0.0` | Allow |

#### PR Merge Validation

| Pattern | Example | Action |
|---------|---------|--------|
| Basic merge | `gh pr merge 123` | Block |
| With flags | `gh pr merge 123 --squash` | Block |
| Delete branch | `gh pr merge --delete-branch` | Block |
| Auto merge | `gh pr merge --auto` | Block |
| Chained | `gh pr create && gh pr merge` | Block |

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
| Allow `gh pr merge` with `--auto` | Still bypasses human review |

## Consequences

### Positive

- Enforces PR workflow for protected branches
- Requires human approval for all PR merges
- Catches chained commands
- Consistent with existing validation pattern

### Negative

- Adds subprocess call to check current branch for bare `git push`
- Slightly longer hook execution (~10ms)
- Agent cannot complete merge workflow autonomously (by design)

## Approval Checklist

### Push Validation (v0.5.0)

- [x] Hook implementation tested with edge cases
- [x] Unit tests added
- [x] E2E test added
- [x] README updated

### PR Merge Validation (v0.6.0)

- [ ] Hook implementation for `gh pr merge` blocking
- [ ] Unit tests added
- [ ] E2E test added
- [ ] README updated
