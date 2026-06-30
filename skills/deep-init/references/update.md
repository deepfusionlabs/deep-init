# update.md — C8 Updater (`--update` / `--lint`)

Keeps the output proportional to what changed. Reads `.file_hashes.json` + `manifest.json` (written by `generation.md`). Two paths: `--update` (re-analyze the blast radius, spends tokens) and `--lint` (staleness audit, **zero tokens**).

## `--update` flow
**Step 0 — change detection.** The **authoritative** detector is a **symmetric set-diff** of the stored `.file_hashes.json` against a fresh `content_hash` scan over the current source tree (via the file-source ladder in `detection.md`: `git ls-files` → `find`). For every key in `keys(stored) ∪ keys(current)`: **present-only** → new component (full analysis); **stored-only** → **removed** (Step 3 archives it — this is the deletion case a one-directional "for each *current* component" loop silently misses); **in both with a changed `content_hash`** → dirty. `content_hash` is computed over each component's **live member set** (current longest-prefix membership, not the stored file list); a changed file outside every component → the virtual **`shared`** component (a first-class hashed pseudo-component) that flags ALL importers. `git diff --name-only {last_run}..HEAD` and `.ai/docs/current/.pending_changes.txt` (from the commit hook) are **advisory accelerators only** (R8 ladder): consume them when resolvable; **drop them silently** when the repo is non-git, the `{last_run}` ref is unreachable (shallow / squashed / rewritten — reuse `detection.md`'s shallow preflight), or the pending file is absent. Missing `.file_hashes.json` → full run (a user-invoked `refresh`/`--update` that finds no prior output proceeds as an ordinary **first run** — present the standard run-start prompt's plain framing per `SKILL.md`, **not** an improvised lifecycle line like "no prior DeepInit output exists" or "a refresh becomes a full first-time analysis"; R10). **Never skip a changed or removed component because a git input failed.**

**Step 0b — rebuild the structural graph (deterministic, 0-token).** Re-run the Detect-stage **structural-graph build only** — Graphify (`graphify update <path> --no-cluster`) + `tools/graphify_adapter.py` → a fresh `.ai/docs/current/structural-graph.json` (grep-inferred fallback when Graphify is absent, the same ladder `detection.md` uses). This is the cheap, **no-LLM** part of Detect; the token-spending component analysis stays **incremental** (the dirty set below) — `refresh` does NOT become a full run. It closes the freshness gap where `--update` rebuilt the report off a months-old graph: the Map, the IF-8/IF-3a edge inputs, **and** DP-1's `interface_hash` (Step 2, computed from this graph) now all reflect current code. Honour the same side-effect discipline as Detect (`graphify-out/` stays in the always-skip set; run against a copy / clean it when the tree must stay pristine). If Graphify is unavailable **and** no grep fallback can run, **reuse the prior `structural-graph.json` and mark the Map stale** (the report's `as_of` provenance carries its true date) — never silently present an old graph as current, and never block the update (R8 honest-degrade).

**Step 1 — dirty set.** Mark a component dirty if its `content_hash` changed. Then propagate (DP-1, below). Order the dirty set by dependency (leaves first) and by git churn (high-churn first).

**Step 2 — DP-1 interface-hash propagation (the skip).**
For each dirty component, recompute its `interface_hash` (SHA256 of its public surface — exported symbols/signatures from `structural-graph.json`):
- If a component's **`content_hash` changed but its `interface_hash` did NOT**: re-analyze that component, but its **dependents are NOT marked dirty** — their view of this dependency is provably unchanged, so re-analyzing them would produce identical output (pure wasted tokens).
- If a component's **`interface_hash` changed** (a public/breaking change): mark its **transitive dependents** dirty too (`imported_by` closure). **Symbol-level narrowing (v2 edge classes):** when the change is attributable to specific exported symbols AND the v2 graph carries per-symbol edge lists, narrow the re-marked set to the dependents that actually reference those symbols — `graphify_adapter.symbol_dependents(graph, component, symbol)` over `imports_from`/`calls_into`/`inherits_from` — so a change to one symbol no longer needlessly re-analyzes importers that only use a *different* symbol of the component. **Fall back to the full `imported_by` closure** when the edge is coarse (a wildcard/namespace import with no symbol list, or the grep fallback): narrowing is **precision-only** and never drops a real dependent.
This is a re-run-time optimization only — no quality cost, fully reversible (drop the optimization → re-analyze all dependents → identical result). The always-re-run-horizontal pass (Step 4) is the safety net.

**Step 3 — re-analyze.** Run `extraction.md` (+ `database.md` if data models changed) on the dirty set only, in dependency order, injecting prior dependency analyses for dependents. New components → full analysis. Removed components → move their docs to `.ai/docs/archive/` (don't delete).

**Step 4 — always re-run horizontal.** Run `horizontal.md` (all six cross-cutting docs) regardless of which components changed — cross-component effects (a new circular dep, a shifted workflow, a bounded-context clash) aren't visible from a single component's diff. Cheap relative to component re-analysis; this is what makes the DP-1 skip safe.

**Step 5 — filter → redact → verify → emit.** Re-run Filter on changed findings; Redact; re-run Verification (citations may have moved); regenerate only the affected lean/deep files (owned-region writes, `.bak`). Classify each change ADDED / MODIFIED / BREAKING and append to `changelog.md`. Update `.file_hashes.json` + `manifest.json`.

**`--update --review`** runs review cycles over the changed set after Step 5.
**`--update --components=a,b`** limits the dirty set to the listed components; if changes are detected OUTSIDE them, **warn** ("changes in {x} not covered by --components; run without --components or add them") and proceed with the listed set. *(Resolves v1 open question: warn, don't silently skip.)*

## `--lint` flow (zero LLM tokens)
Pure hash/reference comparison — no subagents, no model calls:
1. **Staleness per finding/component:** **fresh** (source `content_hash` unchanged since `verified_at`) / **stale** (source changed since `verified_at`) / **critical** (a cited `file:line` no longer resolves — reuse `verification.md` Pass-1 existence check).
2. **Broken references:** any `file:line` in any doc that doesn't resolve.
3. **ID consistency:** duplicate IDs in a scope; referenced IDs that don't exist; non-contiguous numbering.
4. **Coverage %:** components with docs ÷ components detected; findings verified ÷ total.

Output: a report (per-component fresh/stale/critical counts, broken-ref list, ID failures, coverage), exit non-zero if any `critical` — suitable for CI. Spends **0 tokens** (assert this; any model call here is a bug).

## `--update-adr` (extended to BR + issues)
Delegates to `adr.md`: re-check existing ADRs against current code → CONFIRMED / DRIFTED / EVIDENCE-MISSING. No full re-analysis. **Extension:** `--recheck=adr,rules,issues` extends this same CONFIRMED/DRIFTED recheck to **business rules and open issues over the DP-1 blast radius** (the changed components + their interface-dirty dependents) — reusing the existing mechanism, not a new traversal. A BR whose implementing code changed is re-verified; an open issue whose provenance falls in the dirty set is re-detected and its lifecycle updated (below).

## Issue baseline + lifecycle diff (T5.1)
`.ai/docs/.issue_baseline.json` lives **beside `.file_hashes.json`** and is **written every run**. It records accepted/known issues keyed by the **shared match key** `(family, normalized file:line ± symbol)` defined in `issues.md` — **NOT** the `content_hash`/`interface_hash` SHAs (unrelated; never derive from them).

On each `--update`/heal run, after issue re-detection — which rides Step-4's **always-re-run-horizontal** (issues are re-detected at **horizontal scope**, never per-dirty-component, so a dependent-anchored IF-3a/IF-1 issue can't go stale behind the DP-1 skip) — diff the detected set against the baseline:
- **new** — detected, not in baseline.
- **persisting** — detected, in baseline, still open.
- **accepted** — accepted via `--issues-baseline=accept` → suppressed from "new" (still listed).
- **resolved** — was open, no longer detected AND re-verified gone (`verification.md` Pass-1 confirms the cited construct is gone).
- **regressed** — re-detected after having been resolved → flagged against the **original** accepted baseline, never silently re-accepted.

**Line-shift robustness:** the match key keys on the enclosing symbol (not the raw line) and re-resolves on `SYMBOL_MOVED` (reuse `verification.md` Pass-1); re-keying is scoped to the DP-1 blast radius so an untouched component's issues never churn. `resolved`/`regressed` transitions append to the `changelog.md` **issue section**. Acceptance is user-driven + **write-once-per-id** (no auto-accept on first run — that would hide real findings); `--issues-baseline=reset` clears it.

**`--lint` stays zero-token:** it may flag that a baselined issue's citation no longer resolves (a *candidate* resolved/critical, deterministic via Pass-1) but it **never re-detects** — full lifecycle transition is an `--update`/heal action. Any model call on `--lint` is a bug.

## Staying fresh — notify / session-start / auto-update (see `triggers.md`)
A git hook **cannot** summon a Claude session, so nothing re-analyses on its own. `setup-hooks`
instead installs the deterministic keystone `assets/deepinit_status.py` (the no-LLM core of
`--lint`) plus three escalating, independently-toggled triggers — `notify-on-commit` (default on:
the post-commit hook prints a staleness nudge), `check-on-session-start` (default on: a SessionStart
hook surfaces staleness), and `auto-update` (default **off**: a detached headless `claude -p`
actually runs `--update` after a source commit, never auto-committing). The first two are 0-token;
only `auto-update` spends tokens, which is why it is opt-in. **`post-commit.sh` only records the
changed files + optionally nudges — it never silently updates.** Full mechanics, the config keys,
and the six auto-update safeguards live in `triggers.md`.
