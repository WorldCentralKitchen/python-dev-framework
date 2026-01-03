# ADR-014: Design Patterns Skill

| Field | Value |
|-------|-------|
| Status | Proposed |
| Date | 2026-01-02 |
| Deciders | TBD |
| Related | [ADR-004](004-prescribed-dependencies.md), [ADR-011](011-type-import-standards.md), [ADR-013](013-immutability-safety-patterns.md) |

## Context

Python developers often apply Gang of Four patterns verbatim from Java/C++ without adapting to Python idioms:

- Singleton classes when modules already are singletons
- Deep inheritance hierarchies when composition works better
- Verbose factory classes when callable functions suffice
- Missing SOLID principles in code organization

A skill providing Pythonic pattern guidance improves code quality and prevents over-engineering.

## Decision

### 1. Skill Scope

| Category | Included Patterns |
|----------|-------------------|
| Creational | Factory Method, Abstract Factory, Builder |
| Structural | Composite, Decorator, Flyweight, Adapter, Facade |
| Behavioral | Strategy, Observer, Iterator, Command, State |
| Python-specific | Global Object, Prebound Method, Sentinel |
| Principles | All 5 SOLID principles |
| Anti-patterns | Singleton abuse, inheritance overuse, Java-isms |

### 2. Excluded Patterns

| Pattern | Reason |
|---------|--------|
| Singleton | Python modules are singletons |
| Prototype | `copy.copy()` is sufficient |
| Bridge | Rarely needed in dynamic languages |
| Visitor | Double dispatch unnecessary with duck typing |
| Memento | `pickle`/`dataclass` handles serialization |

### 3. Content Philosophy

Based on Brandon Rhodes' guidance[^1]:

> "Modern Python simply avoids the problems that the old design patterns were meant to solve."

| Principle | Implementation |
|-----------|----------------|
| Functions first | Prefer functions over classes for behavior |
| Callables | Use `Callable` protocol for strategies/factories |
| Protocols | Use `Protocol` for interface segregation |
| Composition | Prefer over inheritance |
| Module-level | Use for global objects (not singleton classes) |

### 4. Skill Structure

| Component | Purpose |
|-----------|---------|
| `SKILL.md` | Quick reference tables, triggers, overview |
| `references/solid-principles.md` | Detailed SOLID with Python examples |
| `references/anti-patterns.md` | What to avoid with alternatives |
| `references/creational-patterns.md` | Factory, Builder patterns |
| `references/structural-patterns.md` | Composite, Decorator, Flyweight |
| `references/behavioral-patterns.md` | Strategy, Observer, Iterator |
| `references/python-idioms.md` | Global Object, Prebound, Sentinel |

### 5. Content Guidelines

| Guideline | Rationale |
|-----------|-----------|
| Tables over prose | LLM context efficiency |
| ~15-line code examples | Minimal but complete |
| Good/Bad pairs | Clear contrast |
| ~100-200 lines per file | Fits context window |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Single monolithic file | Too large for LLM context |
| GoF-faithful implementations | Not Pythonic |
| No anti-patterns section | Misses important guidance |
| Separate SOLID skill | Tightly coupled to pattern decisions |
| All 23 GoF patterns | Many unnecessary in Python |

## Consequences

### Positive

- Consistent Pythonic patterns across codebase
- Reduced over-engineering (no unnecessary Singleton classes)
- Better SOLID adherence
- Clear anti-pattern avoidance guidance
- Composition over inheritance culture

### Negative

- Learning curve for Java/C++ developers
- May conflict with existing codebases using traditional patterns
- Opinionated choices may not fit all use cases

### Risks

| Risk | Mitigation |
|------|------------|
| Over-simplification | Include nuanced "when to use" guidance |
| Outdated content | Reference authoritative sources with dates |
| Pattern conflicts | Document when traditional patterns are valid |

## References

- [Brandon Rhodes - Python Design Patterns](https://python-patterns.guide/)[^1]
- [faif/python-patterns GitHub](https://github.com/faif/python-patterns)
- [tuvo1106/python_design_patterns](https://github.com/tuvo1106/python_design_patterns)
- [The Little Book of Python Anti-Patterns](https://docs.quantifiedcode.com/python-anti-patterns/)
- Raymond Hettinger - "Transforming Code into Beautiful, Idiomatic Python"

[^1]: Brandon Rhodes, PyCon 2025 Keynote: "The modern Python programmer spends little time thinking about the classic 'Design Patterns' of the 1990s... modern Python practices simply avoid the problems that the old design patterns were meant to solve."

## Approval Checklist

- [ ] SKILL.md created with frontmatter and quick reference
- [ ] All 6 reference files created
- [ ] docs/adr/README.md updated with ADR-014
- [ ] Skill triggers tested with Claude Code
- [ ] Cross-references to ADR-011, ADR-013 verified
