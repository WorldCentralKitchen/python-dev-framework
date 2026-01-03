# Architecture Decision Records

## Index

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [ADR-001](001-python-dev-framework-architecture.md) | Framework Architecture | Proposed | Plugin-based enforcement using uv, Ruff, Black, mypy, cchooks |
| [ADR-002](002-two-layer-enforcement-model.md) | Two-Layer Enforcement | Proposed | Claude hooks (real-time) + pre-commit (git-level gate) |
| [ADR-003](003-configuration-strictness-levels.md) | Strictness Levels | Proposed | strict/moderate/minimal configuration via settings.json |
| [ADR-004](004-prescribed-dependencies.md) | Prescribed Dependencies | Proposed | pydantic, structlog, useful-types, pytest ecosystem |
| [ADR-005](005-testing-coverage-strategy.md) | Testing Coverage | Proposed | 75% minimum threshold, critical path requirements |
| [ADR-006](006-e2e-testing-strategy.md) | E2E Testing | Proposed | CLI subprocess tests with --plugin-dir |
| [ADR-007](007-plugin-dogfooding.md) | Plugin Dogfooding | Proposed | Self-host plugin during development |
| [ADR-008](008-linting-rule-strategy.md) | Linting Rule Strategy | Proposed | Expanded Ruff rules, E731/SLF001/PLR0915 decisions |
| [ADR-009](009-lsp-integration.md) | LSP Integration | Proposed | Ruff LSP server for real-time diagnostics |
| [ADR-010](010-python-version-compatibility.md) | Python Version Compatibility | Proposed | 3.9-3.13 support, typing_extensions, __future__ |
| [ADR-011](011-type-import-standards.md) | Type Import Standards | Proposed | typing vs collections.abc, PEP 585/604 |
| [ADR-012](012-source-directory-layout.md) | Source Directory Layout | Proposed | types/, models/, _internal/ conventions |
| [ADR-013](013-immutability-safety-patterns.md) | Immutability Patterns | Proposed | Tuple preference, SequenceNotStr, frozen dataclasses |
| [ADR-014](014-design-patterns-skill.md) | Design Patterns Skill | Proposed | Pythonic GoF patterns, SOLID principles, anti-patterns |

## Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                      ADR-001: Architecture                       │
│              (Plugin structure, technology stack)                │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    ADR-002      │ │    ADR-004      │ │    ADR-005      │
│   Enforcement   │ │  Dependencies   │ │    Testing      │
│     Model       │ │                 │ │                 │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   │
┌─────────────────┐ ┌─────────────────┐          │
│    ADR-003      │ │   ADR-010/013   │◄─────────┘
│   Strictness    │ │  Version/Types  │
└────────┬────────┘ └─────────────────┘
         │
         ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│    ADR-008      │───│    ADR-011      │───│    ADR-012      │
│    Linting      │   │  Type Imports   │   │  Dir Layout     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## Decision Dependencies

| ADR | Depends On | Depended By |
|-----|------------|-------------|
| ADR-001 | — | ADR-002, ADR-003, ADR-004, ADR-005, ADR-008, ADR-010, ADR-012 |
| ADR-002 | ADR-001 | ADR-003 |
| ADR-003 | ADR-001, ADR-002 | ADR-005, ADR-008 |
| ADR-004 | ADR-001 | ADR-010, ADR-013 |
| ADR-005 | ADR-001, ADR-003 | — |
| ADR-006 | ADR-005, ADR-007 | — |
| ADR-007 | ADR-001 | ADR-006 |
| ADR-008 | ADR-001, ADR-004 | ADR-011, ADR-013 |
| ADR-009 | ADR-008 | — |
| ADR-010 | ADR-001 | ADR-011 |
| ADR-011 | ADR-008, ADR-010 | ADR-014 |
| ADR-012 | ADR-001, ADR-004 | — |
| ADR-013 | ADR-004, ADR-008 | ADR-014 |
| ADR-014 | ADR-004, ADR-011, ADR-013 | — |

## Coverage Matrix

Maps plan decisions to ADRs:

| Plan Decision | ADR Coverage |
|---------------|--------------|
| Scope: enforcement only | ADR-001 |
| Package manager: uv | ADR-001 |
| Distribution: Claude Code Plugin | ADR-001 |
| Linting: Ruff + Black | ADR-001, ADR-002, ADR-008 |
| Type checking: mypy strict | ADR-001, ADR-002 |
| Git workflow: Conventional Commits | ADR-002, ADR-003 |
| Python version support | ADR-001, ADR-010 |
| Hook strategy: save-level | ADR-002 |
| Validation: Pydantic | ADR-004 |
| Logging: structlog | ADR-004, TDD-002 |
| Hook SDK: cchooks | ADR-001, ADR-004 |
| Error handling: fail closed | ADR-001 (TDD-001 details) |
| Testing: 75% coverage | ADR-005 |
| Strictness levels | ADR-003 |
| Two-layer enforcement | ADR-002 |
| Type import standards | ADR-011 |
| Directory layout | ADR-012 |
| Immutability patterns | ADR-013 |
| Extended linting rules | ADR-008 |
| LSP integration | ADR-009 |
| Design patterns skill | ADR-014 |

## Related Documents

| TDD | Title | Related ADRs |
|-----|-------|--------------|
| [TDD-001](../tdd/001-plugin-implementation.md) | Plugin Implementation | ADR-001, ADR-002, ADR-003 |
| [TDD-002](../tdd/002-gcp-logging-integration.md) | GCP Logging Integration | ADR-004 |
| [TDD-003](../tdd/003-python-version-patterns.md) | Python Version Patterns | ADR-010 |
| [TDD-004](../tdd/004-type-import-patterns.md) | Type Import Patterns | ADR-011 |
| [TDD-005](../tdd/005-directory-layout-templates.md) | Directory Layout Templates | ADR-012 |
| [TDD-006](../tdd/006-immutability-patterns.md) | Immutability Patterns | ADR-013 |
