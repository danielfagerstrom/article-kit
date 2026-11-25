# ADR-0003 — A `\lean{}` tag is compared with full, namespace-qualified names

- **Status:** Accepted (2026-11-25)
- **Mechanism:** `artifacts.declared_names`, `artifacts.Scope` and `artifacts.resolve_lean_name`;
  check 1 in `checks.py`; the pin and shadow readers in `boundary.py`; `closure.scan_lean`.

## Context

The declaration reader stopped at the first dot, so `theorem SymLevyData.hasTriplet` was recorded
as `SymLevyData`, and check 1 compared only the last segment of the tag. A correct dotted tag
failed as undeclared, and a tag naming `CarriesLatticeLadder.knot_data` passed because an
unrelated `knot_data` existed in another namespace (Q-0876; pyramids PR #96).

## Decision

A declaration is recorded under its full name: the enclosing `namespace` blocks (`section` and
`mutual` blocks nest and `end` closes them; `_root_.` escapes) prefix the written name. A tag
resolves when it equals a declared name or one is the other's dotted suffix (the tag carries a
library prefix the source leaves implicit). Otherwise the last segment alone resolves it only when
the tag has at most two components (`Lib.foo`) and that segment is unique among the declarations.

## Consequences

- Tags that passed on a coincidence of last segments (three or more components, nothing declared
  under that qualification) are now fatal; an article rebinds them to the declaration it means.
- `manifest.lean_decls` lists full names.
- `closure.DeclIndex.resolve` uses the same rule as check 1 (`artifacts.lean_name_matches`), so the
  two readers agree on a tag; a tag with more than one extra leading component over a root-level
  name does not match it. A *source token* (a use inside a proof) then falls back to a unique final
  component at any length, as before: a token is often a field-notation chain on a local
  (`D.jumpPart.exponent_le_sq_at`), whose leading components name no namespace. Without the
  fallback the affine module's closure of `exponent_gaussian_limit` fell from 215 declarations to 7.
