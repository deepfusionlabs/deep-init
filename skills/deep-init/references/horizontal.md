# horizontal.md — Cross-cutting Analysis (Wave 3–4)

System-wide analysis that no single-component pass can see: how components relate, how data flows across them, the domain model, end-to-end workflows, and the cross-reference map. Runs after all component extractions complete. **Always re-runs on `--update`** (it's the cheap safety net that catches cross-component effects — see `update.md`).

> **Operator decision (Option 1, locked):** produce the **full five** deep cross-cutting docs below in `.ai/docs/`. Their highest-value, non-obvious findings are promoted to the lean tier by the Filter; the comprehensive versions live in the deep tier (D2-020 — deep tier stays comprehensive).

> **Default emission (mandatory — backlog B1).** A bare full `deep-init` run must **always emit all six** whole-system docs — `technical-dependencies.md`, `data-layer.md`, `domain-model.md`, `functional-workflows.md`, `cross-references.md`, `shared-state-conflicts.md` — by default, **never silently omit** them on a small/mid repo (the B1 under-emit failure: the kemal e2e run produced only `decisions.md`+`issues.md`). When a concern is genuinely thin (e.g. no database → `data-layer.md`), emit a **short, explicit "not applicable — <reason>" stub** rather than dropping the file. The only honest skip is a **Tiny single-component** target, where the whole-system view collapses into the root `AGENTS.md` and that fold is **stated** in the run summary. The emitted set is verified by generation.md's **Emit-completeness** pre-finalize check (harness §59).

Each sub-stage is a Task subagent reading ONLY prior `.ai/docs/current/` outputs (+ targeted code reads), per global-rules §R2.

## 3a → `technical-dependencies.md`
- **Dependency graph** (Mermaid + table) from `structural-graph.json` / `imported_by` maps.
- **Circular dependencies** (CRITICAL flag) — cycles in the import graph.
- **Coupling analysis** — afferent/efferent per component; identify highly-coupled hubs.
- **Cascade risk** — "if component X changes, what's affected?" (its `imported_by` closure). Feeds `--update` blast-radius reasoning.

## 3b → `data-layer.md`
- **Entity↔table mapping** — every ORM entity ↔ live DB table, with status `✓ mapped` / `⚠️ column mismatch` / `❌ orphan table` / `❌ no table found`.
- **Schema Drift Report** — differences between code expectations and the actual DB schema; per drift: entity, expected (code), actual (DB), severity, impact. *(The field/type-level version of this is computed in `database.md`; this doc aggregates it system-wide.)*
- **Data-access patterns** — repositories / query objects / raw SQL hot spots; N+1 risks if visible.

## 3c → `domain-model.md`
- **Ubiquitous language** — the domain glossary (terms + meaning + where used).
- **Bounded contexts** — which components own which concepts; where the same term means different things in different contexts (flag explicitly — a classic non-obvious gotcha).
- **Domain rules `DR-{nnn}`** — system-wide business rules that transcend any single component (aggregated/promoted from component `BR-`).
- **Concept ownership** — for each core entity, the authoritative component (and any shadow copies).

## 3d → `functional-workflows.md`
- **Use cases `UC-{nnn}`** — actor, goal, preconditions, main flow, alternates.
- **Feature → component map** — which components collaborate to deliver each feature.
- **End-to-end traces** — cross-component workflows `WF-{nnn}` followed step-by-step (`action → file:line`, hopping components), with state transitions and error handling.
- **User stories `US-{nnn}`** + **BDD scenarios** (Given/When/Then) for the key journeys.
- **Workarounds `WA-{nnn}`** — cross-cutting hacks/temporary fixes that are actually load-bearing (high non-obviousness).

## 3e → `shared-state-conflicts.md`
A **write-conflict correlation** pass — the cross-cutting view that turns "these components are coupled" (IF-3a) into "and one may silently overwrite another's write." It is built **only from outputs the pipeline already produced** — the IF-3a `≥2-writer` shared-resource set, `data-layer.md`'s entity↔table mapping, `domain-model.md`'s concept-ownership, and each component's extracted guards / `BR-`s — so it adds **no new all-pairs code scan** (the horizontal pass is the one R2-faithful place that may legitimately see all writers of a shared table together). This doc is **context, not a verdict on correctness**: it flags-don't-asserts and **never enters the lean tier** (R9).

For every shared **mutable** table (a table UPDATE/upsert/DELETE-written by **≥ 2 writers**; an **append-only INSERT** sink — an audit/event log never read back into a business branch — is **excluded**, not a conflict), emit one row group:

| table | writer (component / inferred **external actor**) | columns written | op | guard READ before the write (`file:line`) | guard-shape |

- **guard-shape ∈ {none · compound · asymmetric · full · disjoint}.** `none` (no guard before the overwrite), `full` (origin/owner/version-scoped for **every** state the other writer can be in), and `disjoint` (the writers touch non-overlapping columns) are **deterministic** structural reads. **`compound`** (the guard fires only on `A AND B`, so it covers a *subset* of the other actor's states) and **`asymmetric`** (the guard covers one direction/path but not its mirror — e.g. blocks an *earlier* timestamp yet allows a *later* one) are **semantic judgements**: tag them `[MEDIUM]` and **flag-don't-assert** — they are NOT structural, so any future detector built on them must take the forced R1.5 validate and **never join the deterministic skip-set** (`issue-filter.md`).
- **Per-table verdict** (over the matrix): **SERIALIZED** (every overlap is covered by a row lock / unique-or-exclusion constraint / transactional CAS / an optimistic-lock version column) · **OWNED** (one writer per column-set — `disjoint`) · **CONFLICT** (≥ 2 writers overwrite **overlapping** columns AND ≥ 1 guard is `none` / `compound` / `asymmetric` w.r.t. the other writer's origin). Every **CONFLICT** row names the overlapping column(s) + the offending guard's `file:line`, so the verdict stays a **checkable observation**, never a "this is a bug" claim.
- **Inferred external actor.** A writer may be an out-of-repo actor surfaced by `extraction.md`'s **Q13** (a read-side guard on a value no in-repo code writes); list it as the writer of the column(s) it stamps, grounded to the read-side `file:line` that proves it, `[MEDIUM]`/observation only.
- The **CONFLICT** rows are the deterministic input to a **deferred, report-only** write-conflict detector (the issue family is **not shipped** — see the measured DEFER in `docs/deepinit-phase2-plan.md` + `.ai/docs/decisions.md`); shipping the matrix as **context** is the low-risk half that closes the synthesis gap now.
- **Not applicable** (no shared mutable table — e.g. no database, or every shared table is single-writer/append-only) → emit a short explicit `"not applicable — no shared mutable table"` stub, **never a silent omission**.

## Wave 4 → `cross-references.md`
- **`BR` → `WF` map** — which workflows enforce which business rules.
- **Coverage gaps** — `BR-` enforced by no workflow; workflows governed by no rule; entities with no relationships; integration points with no workflow step.
- **Known deficiencies** — consolidated tech-debt / risk register across components (from each component's Legacy Warnings + the review cycles).
- **Traceability** — feature → component → workflow → rule → file:line chains for the core capabilities.

## `--horizontal` / `--horizontal-only`
`--horizontal` runs this stage standalone (refresh cross-cutting docs without re-extracting components); `--horizontal-only` does only this and skips generation of component files. Useful after small component edits to refresh the system view cheaply.

## Notes
- All findings carry `file:line` and certainty (global-rules §R1).
- Cross-cutting findings flow through the Filter (§R9) like any other; the deep docs stay comprehensive, the lean tier gets only the load-bearing, non-obvious, cross-component facts (e.g. a circular dependency, a bounded-context term clash, a load-bearing workaround).
