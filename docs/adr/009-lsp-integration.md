# ADR-009: LSP Integration for Real-Time Diagnostics

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-29 |
| Deciders | TBD |
| Related | [ADR-002](002-two-layer-enforcement-model.md), [ADR-008](008-linting-rule-strategy.md) |

## Context

ADR-008 identified LSP integration as a future enhancement for real-time diagnostics. Testing confirmed Claude Code supports plugin-based LSP configuration via `.lsp.json`.

### Current Enforcement Model

| Layer | Trigger | Latency | Action |
|-------|---------|---------|--------|
| PostToolUse hook | After Edit/Write | ~1-2s | Auto-fix + format |
| Pre-commit | Git commit | ~2-3s | Block on errors |

### Gap

Developers don't see issues until after edits complete. Real-time feedback would catch problems earlier.

## Decision

### 1. Add Ruff LSP Server

Configure `.claude-plugin/.lsp.json`:

```json
{
  "python": {
    "command": "ruff",
    "args": ["server"],
    "extensionToLanguage": {
      ".py": "python",
      ".pyi": "python"
    }
  }
}
```

Reference in `plugin.json`:

```json
{
  "lspServers": "./.lsp.json"
}
```

### 2. Three-Layer Enforcement Model

```
┌─────────────────────────────────────────────────┐
│ Layer 1: LSP (Real-time)                        │
│ - Diagnostics as code is written                │
│ - No file modification                          │
├─────────────────────────────────────────────────┤
│ Layer 2: PostToolUse Hook (After Edit)          │
│ - Auto-fix safe issues                          │
│ - Format code                                   │
├─────────────────────────────────────────────────┤
│ Layer 3: Pre-commit (Git Gate)                  │
│ - Final validation before commit                │
│ - Block on any remaining errors                 │
└─────────────────────────────────────────────────┘
```

### 3. Global Ruff Requirement

Claude Code's LSP doesn't support variable substitution (`${CLAUDE_PLUGIN_ROOT}`, `${workspaceFolder}`) in command paths. Ruff must be globally installed:

```bash
brew install ruff
```

This is documented in README.md under Prerequisites.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Relative path with wrapper script | `${CLAUDE_PLUGIN_ROOT}` not expanded in LSP config |
| venv-relative path | Not portable across machines |
| LSP-only (no hooks) | Hooks provide auto-fix; LSP is informational only |

## Consequences

### Positive

- Real-time feedback without waiting for edit completion
- Issues visible before hook runs
- Consistent diagnostics between LSP and hooks (both use Ruff)

### Negative

- Requires global ruff installation (not managed by uv)
- Two Ruff processes (LSP server + hook invocation)

### Risks

| Risk | Mitigation |
|------|------------|
| Version mismatch (global vs venv) | Document minimum version requirement |
| LSP overhead | Ruff is fast; minimal impact |

## Approval Checklist

- [ ] LSP configuration tested
- [ ] Global ruff requirement documented
- [ ] README updated with prerequisite
