---
name: plugin-versioning
description: >
  Guide for versioning and releasing Claude Code plugins. Covers semantic
  versioning, CHANGELOG maintenance, and the automated release workflow.
triggers:
  - version
  - release
  - tag
  - changelog
  - semver
  - bump version
---

# Plugin Versioning Guide

## Semantic Versioning for Plugins

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Breaking: hook behavior, removed features | MAJOR | 1.0.0 → 2.0.0 |
| New: skill, command, agent, feature | MINOR | 1.0.0 → 1.1.0 |
| Fix: bug fix, typo, docs | PATCH | 1.0.0 → 1.0.1 |

## Release Checklist

1. **Update CHANGELOG.md**
   - Move items from `[Unreleased]` to new version section
   - Add release date

2. **Update plugin.json version**
   ```json
   {
     "version": "1.1.0"
   }
   ```

3. **Commit release**
   ```bash
   git add CHANGELOG.md .claude-plugin/plugin.json
   git commit -m "chore: release v1.1.0"
   ```

4. **Create and push tag**
   ```bash
   git tag v1.1.0
   git push origin main v1.1.0
   ```

5. **Automated steps** (GitHub Action handles these)
   - Creates GitHub Release with auto-generated notes
   - Opens PR on marketplace repo to update version
   - Human reviews and merges marketplace PR

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/):

```markdown
## [Unreleased]

## [1.1.0] - 2025-01-15

### Added
- New plugin-versioning skill

### Changed
- Updated hook timeout from 10s to 15s

### Fixed
- Fixed edge case in branch name validation
```

## Version Locations

| File | Field |
|------|-------|
| `.claude-plugin/plugin.json` | `"version": "X.Y.Z"` |
| `CHANGELOG.md` | `## [X.Y.Z] - YYYY-MM-DD` |
| Git tag | `vX.Y.Z` |

## Pre-release Versions

For beta or release candidate versions:

```bash
git tag v1.1.0-beta.1
git tag v1.1.0-rc.1
```

Pre-release tags follow semver format and can be used for testing before stable release.
