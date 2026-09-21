# Architecture Decision Records — article-kit

One file per decision, append-only, on the hub's format (`Notes/adr/README.md`). An ADR is never
edited once accepted: if the thinking changes, write a new ADR and mark the old one
`Superseded by ADR-NNNN`. An ADR records *why*; the mechanism it names (a doc under `docs/`, a
check in `linkage/`, a scaffolded file) is the source of truth for *how*.

A decision belongs here when it is framework-wide: it binds every article repo, or draws a boundary
between article-kit, the hub and the article repos. A decision about one article belongs in that
article's `adr/`; one about the wiki or the programme belongs in the hub's.

## Format

```markdown
# ADR-NNNN — Title

- **Status:** Proposed | Accepted (date) | Superseded by ADR-NNNN (date)
- **Mechanism:** where the resulting rule actually lives

## Context
## Decision
## Consequences
```

## Index

| ADR | decision | status |
|---|---|---|
| [0001](0001-article-kit-owns-the-article-process.md) | article-kit owns the article process, and instruction files hold only instructions | Accepted 2026-09-21 |
