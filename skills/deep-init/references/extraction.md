# extraction.md — C3 Extractor (per-component deep analysis)

Per component, in dependency order, a read-only subagent produces the 11-section analysis. This is the LLM layer (ladder Layer 7) — it reads file content WITH all structural context from `detection.md` Layers 1–6.

## Dependency ordering
1. Read `structural-graph.json` (or build a rough graph from grep imports — `detection.md`).
2. Topological sort → processing order (leaf components first, dependents after).
3. Cycle detected → break arbitrarily, log a warning, continue.

- **Wave 2a — leaf components** (no internal deps): launch in PARALLEL (no prior context needed).
- **Wave 2b — dependent components** (ordered by depth): each subagent receives the completed analyses of its dependencies as context; same-depth components run in parallel.
- `SEQUENTIAL_MODE=true` (Task tool unavailable): run all components inline, one at a time, in dependency order.

Dependency-ordering matters: injecting prior dependency analyses into dependents measurably reduces hallucination (DocAgent ablation).

## Stage-timing emission (manifest schema-5 `processing_metrics`)
At each pipeline stage boundary — and each Wave-2a/2b component sub-agent's start/end — record a
**stage-timing** stamp: the stage name + the engine's best-effort clock. These feed the manifest
`processing_metrics` block (generation.md) and, in a metered validation run, the cost ledger's
`cost.processing{}`. For the parallel Wave 2a, record BOTH `wave_2a_serial_sum_sec` (Σ of each
component's own extraction duration) and `wave_2a_wall_sec` (the wall span of the parallel wave), so
the parallel speedup (`serial_sum / wall`) is derivable. The engine's self-stamps are
`engine_stage_stamps`-grade — they ATTRIBUTE time per stage; the *publishable* wall-clock total is
`external_metered` only (a metered runner observes it externally). Never publish a self-stamp as the
wall-clock total.

**Emit the user-facing progress line at each component boundary too.** Alongside each stage-timing
stamp — and as each Wave-2a/2b **component** finishes — emit the live **progress line** (SKILL.md →
*Progress presentation*): the deterministic `% complete` + the honest time-remaining range
(`tools/progress_model.py` — `percent_complete()` reads the same `completed{}` map, `progress_line()`
renders the plain wording). Extract is the longest stage, so the per-component cadence is what keeps
the bar visibly moving; on a one-component repo this collapses to the per-stage cadence (honest —
nothing finer exists). The line is informational only — it never prompts and never blocks.

## Subagent configuration
For each component in the registry, launch a Task subagent with `agent: Explore`:
- **Tools:** Glob, Grep, LS, Read (read-only).
- **Scope:** ONLY files within the component's path (global-rules §R2).
- **Method:** layered detection (`detection.md`).

## Subagent prompt template
```
Analyze the component at {component_path}. This is a {architecture_style} project using {tech_stack}.
This project is a {business_domain} system serving {target_users}. (from discovery.md)

For each feature and workflow, describe:
- The BUSINESS CAPABILITY it provides (not just what the code does technically)
- WHO uses it and WHY (user perspective)
- The BUSINESS IMPACT if it fails or is unavailable

Read references/global-rules.md for mandatory rules.

[Default / thorough]: Read ALL source files in this component. Do not skip any.
[If --depth=fast]: Use layered detection — grep for patterns first, then deep-read only flagged files.

[If Wave 2b — dependent component]: These components are already analyzed; use their
analysis as context for imports/integrations: {dependency_analyses}

Produce output with ALL sections below. Write to .ai/docs/current/components/{component_name}.md
For EVERY finding (BR-/WF-/IP-xxx) include (verified: {ISO date}). Tag [HIGH] or [MEDIUM] certainty.
```

## Verification checklist (13 questions — run before submitting)
**Structure:** (Q1) entry points? (Q2) external systems it talks to? (Q3) what it exposes to other components? (Q13) external-actor inference — is there a read-side guard on a value **no in-repo code writes** (an inferred out-of-repo writer)? (see *External-actor inference* below)
**Behavior:** (Q4) state transitions it manages? (Q5) validation rules it enforces? (Q6) error/failure modes?
**Behavioral / relational facts** (the most under-captured kinds — extract these as deliberately as structure; see §"Behavioral & relational facts" below): (Q10) the **key invariants** it relies on or maintains — value-semantics / immutability (returns a new copy vs mutates in place), never-empty / always-contains / ordering invariants, the core data structure and its load-bearing property, and lifecycle invariants (the ORDERED phases this subsystem is started / stopped / notified in)? (Q11) the **boundary / layer rules** it lives under — the layering direction and what must NOT cross it, what traffic passes through what (a required chain/middleware), error-propagation conventions ("return errors to the caller; do not crash/exit after startup"), and module-isolation rules? (Q12) the **system entry-point / startup workflow** it participates in — the single ordered boot call-chain for the system as a whole (command/main → construct → run → configure → start), recorded once for the owning component?
**Context:** (Q7) what conventions/patterns differ from the rest of the codebase? (Q8) what workarounds / tech debt exist? (Q9) the rationale for non-obvious design choices?

The three **Context** questions are where non-obvious signal originates; **Q10–Q12 are where the highest-value behavioral/relational signal originates** (structural entities are captured well by Layers 1–6; these relational facts are not). The Filter stage (`filter.md`) consumes their answers. If any in-scope question is unanswered, go back and address it before submitting — but obey global-rules R1: cite a `file:line` and tag certainty, and **prefer omission over a guessed invariant/rule** (a confidently-wrong invariant is worse than a gap; an unfounded one goes to Open Questions, never a fabricated `[HIGH]`).

## External-actor inference (Q13 — an out-of-repo writer, recovered from a read-side guard)
A frequent miss on real systems: in-repo code **reads / branches on** a column / enum / id value that **no in-repo code writes** (e.g. it skips rows where `updater == 2`, but nothing in the repo ever sets `2`) — evidence of an **out-of-repo writer** (a desktop client, a partner job, a manual console). Record it as an **inferred external actor** and an `IP-{comp}:{nnn}` of `type=external-actor`, grounded to the **read-side `file:line`** that proves it. This is an **observation, never an assertion** — DeepInit reads only this repo, so it asserts an external writer *exists*, not what its code does. The absence-proof ("nothing writes X") is the higher-FP direction, so keep it conservative:
- **Cap `[LOW]`** and word it as a confirmable observation ("in-repo branches on `X`; no in-repo write of `X` found — external writer inferred, confirm"), never a `[HIGH]` claim.
- **Retract** the inference the moment any in-repo write of the value is found — it was an in-repo writer all along.
- **Suppress** it when the repo persists via **dynamic / reflective** paths a static read can't enumerate (an ORM dirty-field save that writes every changed column, reflection, an interpolated / string-built SQL statement) — otherwise the absence-proof manufactures a phantom actor; state the reduced coverage instead of guessing.

This Q13 signal is the deterministic input the `horizontal.md` §3e write-conflict matrix (`shared-state-conflicts.md`) lists as a shared-table writer.

## Behavioral & relational facts (Q10–Q12 — extract as first-class, file:line-grounded)
Across field runs the engine reliably captures structural entities (components, edges, data-stores, tech choices) but systematically **under-captures three behavioral/relational fact kinds**. Capture each as a normal finding (existing ids, certainty tag, `file:line`); they are NOT a new section — they enrich §3 (Workflows) and §4 (Business Rules):

- **(a) Key invariants → record as `BR-{comp}:{nnn}` (criticality usually Core).** Value-semantics / immutability ("operation returns a new copy, never mutates in place"); never-empty / always-contains / non-null invariants; ordering invariants; the **core data structure and its load-bearing property** (e.g. a persistent/rope/copy-on-write structure that is cheap to clone, enabling snapshots); and **lifecycle invariants** — the ORDERED phases a subsystem is started / stopped / notified in. Ground each to the constructor/builder/method (`file:line`) that establishes or enforces it; an ordered lifecycle whose steps are real call-sites is better recorded as a `WF-` (below).
- **(b) Boundary / layer rules → record as `BR-{comp}:{nnn}` (Core/Supporting).** The layering DIRECTION and what must NOT cross it ("the inner layer depends on nothing outward"); what traffic passes through what ("all X↔Y traffic passes through the middleware/handler chain"); **error-propagation conventions** ("return errors to the caller; do not crash or exit after startup"); and module-isolation rules. These often have NO single enforcing line — ground to the most representative witness (an import-direction example, the chain wiring, the error-return idiom) and tag `[MEDIUM]` when inferred from a consistent pattern rather than a stated rule.
- **(c) System entry-point / startup workflow → record ONCE as a `WF-{comp}:{nnn}` (type: background, or a cross-component `WF-{nnn}` if it spans components).** The single ordered boot call-chain for the system AS A WHOLE — not a per-feature workflow — e.g. `CLI command → construct app → Run → setup config → start service`. Recorded by the component that owns `main`/the entry point, each step an `action → file:line`. Distinguish it from feature workflows by labeling it the system startup/boot sequence.

## The 11 mandatory output sections
1. **Component Overview** — purpose (1–2 sentences); tech stack; key files/entry points (paths); complexity Simple/Moderate/Complex; certainty.
2. **Features & Capabilities** — per feature: description, entry point (file), source files, certainty.
3. **Workflows & Behaviors** — per `WF-{comp}:{nnn}`: type (user-facing/background/scheduled), trigger, steps (`action → file:line`), state transitions, error handling, source files, certainty. **Include the system startup/boot sequence here (Q12)** when this component owns `main`/the entry point — the single ordered boot call-chain for the whole system, labeled as such (one `WF-`, not per-feature).
4. **Business Rules** — table `BR-{comp}:{nnn} | rule | criticality | source(file:line)`. Criticality: **Core** (system breaks without it) / **Supporting** (important, not central) / **Peripheral** (convenience). **Also record key invariants (Q10) and boundary/layer rules (Q11) as `BR-` rows here** (value-semantics/immutability, never-empty/ordering invariants, the core data structure's load-bearing property, lifecycle invariants; layering direction & what must-not-cross, required traffic chains, error-propagation conventions, module-isolation) — these are the under-captured behavioral/relational facts, ground each to its `file:line` witness.
5. **Data Models** — per entity: purpose, source file, property table (property/type/required/description), enumerations, relationships.
6. **Integration Points** — table `IP-{comp}:{nnn} | name | type (API/import/event/shared-DB/file-IO/email/external-actor) | direction (in/out/bi) | target | source`. (`external-actor` = an **inferred out-of-repo writer**, see *External-actor inference* / Q13 below.)
7. **User Roles & Access** — role/permissions/source; auth mechanism + authorization approach.
8. **Interfaces Exposed** — public APIs / shared modules / exported classes other components can use.
9. **Interfaces Consumed** — table `external component | what is imported | import location`. List ONLY — do not analyze the external component.
10. **Legacy Warnings** — dead code; deprecated patterns; tech-debt signals (TODO/FIXME/HACK counts); missing test coverage (test vs source file count); workarounds; safe vs high-risk zones; god objects (>500 LOC, listed).
11. **Design Rationale** — table `pattern | location | rationale | evidence | certainty` for non-obvious choices. Look in: code comments ("decided"/"chose"/"because"), git blame for refactors, README/docs, intentional naming patterns.

## Analysis depth
- **Thorough (DEFAULT)** — read ALL source files regardless of count. The quality-first default (no token shortcut by default).
- **Fast (`--depth=fast`, opt-in)** — for components >30 files: Layer-1 grep scan → identify the 15–20 most important files → deep-read only those → grep context (±5 lines) for the rest → note skipped files. Token-saving; use only when explicitly requested. (Components ≤30 files: read all directly regardless of mode.)

DB analysis for a component's data models is handed to `database.md` (C3-DB) when a database is in scope.
