# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-02

### Added

- Marketplace sync: release workflow now syncs plugin files to marketplace repo
- Self-registering plugins: adds entry to marketplace.json if not exists

### Changed

- Updated plugin-versioning skill with marketplace distribution docs
- Simplified installation docs (removed unsupported version pinning)

## [0.1.0] - 2024-12-30

### Added

- Initial release of Python Development Framework plugin
- PostToolUse hook: Auto-formats Python files with ruff + black
- PreToolUse hook: Validates git branch names and commit messages
- LSP integration with Ruff for real-time diagnostics
- Three strictness levels: strict, moderate, minimal
- Python version detection from pyproject.toml (3.9-3.13)
- `from __future__ import annotations` enforcement in strict mode
- Type import modernization via Ruff UP rules
- Directory layout enforcement via SLF001
- Immutability pattern enforcement (B006, B039, RUF008, RUF012)
- Comprehensive unit tests and E2E test framework
- Plugin versioning skill with release workflow guidance
- Automated release workflow (tag → GitHub Release → marketplace PR)

### Documentation

- ADR-001 through ADR-013 documenting architectural decisions
- TDD-001 through TDD-006 documenting implementation details
- README with installation and configuration instructions

[Unreleased]: https://github.com/WorldCentralKitchen/python-dev-framework/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/WorldCentralKitchen/python-dev-framework/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/WorldCentralKitchen/python-dev-framework/releases/tag/v0.1.0
