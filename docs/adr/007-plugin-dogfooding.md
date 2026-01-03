# ADR-007: Plugin Dogfooding Strategy

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2025-12-28 |
| Updated | 2026-01-02 |
| Deciders | TBD |
| Related | [ADR-006](006-e2e-testing-strategy.md) |

## Context

Developing a Claude Code plugin benefits from using that plugin during its own development ("dogfooding"). This provides immediate feedback on plugin behavior and surfaces usability issues early.

## Decision

Support **two dogfooding modes** depending on development needs:

### Mode 1: Install from Marketplace (Stable)

Use when developing with the latest released version:

```bash
claude plugin install python-dev-framework@WorldCentralKitchen
cd python-dev-framework
claude  # Plugin applies to its own development
```

### Mode 2: Local Plugin (Test Changes)

Use when testing unreleased changes:

```bash
cd python-dev-framework
claude --plugin-dir .  # Loads plugin from current directory
```

## Repository Structure

```
python-dev-framework/
├── .claude-plugin/
│   └── plugin.json           ← Plugin manifest at repo root
├── hooks/
│   ├── hooks.json            ← Hook definitions
│   └── scripts/
│       ├── config.py
│       ├── format_python.py
│       └── validate_git.py
├── skills/
├── tests/
└── docs/
```

### Key Implementation Details

| Aspect | Implementation |
|--------|----------------|
| Plugin location | `.claude-plugin/` at repository root |
| Hook scripts | Must use `uv run python` (not bare `python`) |
| Path resolution | `${CLAUDE_PLUGIN_ROOT}` resolves to repo root |
| Marketplace | Installed via `python-dev-framework@WorldCentralKitchen` |

## Escape Hatches

| Scenario | Solution |
|----------|----------|
| Hook blocks development | Restart without `--plugin-dir` or uninstall plugin |
| Git hook blocks commits | `git commit --no-verify` |
| Need to debug hook | Run script manually with test input |
| Testing clean state | Use fresh terminal without plugin |

## Consequences

### Positive

- Immediate feedback on plugin behavior
- Surfaces bugs and usability issues early
- Plugin quality improves through constant real-world use
- Developers experience what users will experience
- Simple setup: either install from marketplace or use `--plugin-dir .`

### Negative

- Broken hooks can impede development
- Requires understanding escape hatches
- Plugin changes require session restart to take effect

### Risks

| Risk | Mitigation |
|------|------------|
| Recursive blocking | Escape hatches documented |
| Silent failures | Debug mode shows hook execution |
| Stale plugin state | Restart session after changes |
