# ADR-007: Plugin Dogfooding Strategy

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2025-12-28 |
| Deciders | TBD |
| Related | [ADR-006](006-e2e-testing-strategy.md) |

## Context

Developing a Claude Code plugin benefits from using that plugin during its own development ("dogfooding"). This provides immediate feedback on plugin behavior and surfaces usability issues early.

## Decision

Support **self-hosting the plugin** during development using `--plugin-dir .claude-plugin`.

### Plugin Directory Structure

```
wck-claude-plugins/
├── .claude-plugin/           ← Plugin root for --plugin-dir
│   ├── plugin.json           ← Plugin manifest
│   └── hooks/
│       ├── hooks.json        ← Hook definitions
│       └── scripts/
│           ├── config.py
│           ├── format_python.py
│           └── validate_git.py
├── src/                      ← Library source (if any)
├── tests/                    ← Test suite
└── docs/                     ← Documentation
```

### Key Implementation Details

| Aspect | Implementation |
|--------|----------------|
| Plugin location | `.claude-plugin/` contains all plugin components |
| Hook scripts | Must use `uv run python` (not bare `python`) |
| Path resolution | Scripts use `sys.path.insert(0, Path(__file__).parent)` for sibling imports |
| Environment variable | `${CLAUDE_PLUGIN_ROOT}` resolves to `.claude-plugin/` |

### hooks.json Configuration

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "uv run python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/format_python.py"
      }]
    }],
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "uv run python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate_git.py"
      }]
    }]
  }
}
```

### Development Workflow

```bash
# Start Claude with plugin self-loaded
claude --plugin-dir .claude-plugin

# Or create alias for convenience
alias claude-dev='claude --plugin-dir /path/to/.claude-plugin'
```

### Escape Hatches

| Scenario | Solution |
|----------|----------|
| Hook blocks development | Restart without `--plugin-dir` |
| Git hook blocks commits | `git commit --no-verify` |
| Need to debug hook | Run script manually with test input |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Plugin at project root | Clutters project with plugin files |
| Separate test project | Loses immediate feedback loop |
| Disable hooks during dev | Defeats purpose of dogfooding |

## Consequences

### Positive
- Immediate feedback on plugin behavior
- Surfaces bugs and usability issues early
- Plugin quality improves through constant real-world use
- Developers experience what users will experience

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

## Approval Checklist

- [ ] Plugin structure documented
- [ ] Escape hatches tested
- [ ] Development workflow validated
- [ ] README updated with instructions
