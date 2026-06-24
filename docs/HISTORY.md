# HISTORY — errata & corrections log

*Newest first. Every published INDICATIVE number is honest at the time of writing but may be revised as the
corpus grows or an error is found. When a figure on the product page / README is corrected, log it here with
the date, what changed, and why — so a reader can trust that corrections are tracked, not quietly overwritten.
This is the trust-first counterpart to "we under-claim rather than over-claim".*

## 2026-06-13 — Phase 6: Graphify language count VERIFIED at 25 (a self-corrected near-miss)
- **What:** the product page claims DeepInit's AST parser (Graphify) reads "25 languages". During Phase-6 Track 0 an interim re-count briefly "corrected" this to **14** (from a too-narrow regex that only matched the explicit `ts_module=` configs in `extract.py`) and even briefly listed Go as grep-fallback-only. An empirical extraction test then **re-verified the original 25**: `graphify update` on Go/Rust/Elixir/Zig/Julia/Kotlin/Swift/Scala files all produced AST nodes; the extension-dispatch census in `extract.py` shows **25 tree-sitter language grammars** (29 incl. JSON/SQL/Terraform; +Dart/Astro/Svelte/Apex/Razor extractors).
- **Why it mattered / outcome:** the page's "25" was **accurate** — the brief "14" was the error, caught before any commit and reverted everywhere (detection.md + README + page + coverage-matrix + the A/B record). Only **Crystal** and **OCaml** are genuine no-grammar fallbacks. The trigger was an operator question about how Graphify was installed, which surfaced the package's full tree-sitter `Requires` list (Go/Rust/Elixir present) and prompted the re-check — a good example of the verify-don't-assume discipline catching a number before it shipped.
- **Reference:** `validation/graphify/ab-graphify-vs-fallback.json` (`grammars_real: 25`, the correction_note) + the empirical test in test-plan Run 35.

## 2026-06-13 — Phase 6: harness check count is now self-deriving
- **What:** the "150-check / 150/150" figure was hand-transcribed in several places and had begun to drift as the harness grew (now 162). 
- **Fix:** every page/README/CLAUDE.md count now derives from `validation/STATS.json` (built by `tools/build_stats.py`), and `tools/check_stats_drift.py` + the `validate` CI workflow fail on any future drift. The mutation harness (`tests-fixtures-v1/_mutation_harness.py`) proves the gated checks are load-bearing.

## Template for future entries
```
## YYYY-MM-DD — <one-line summary>
- **What:** the figure / claim that changed (old → new).
- **Why:** the cause (corpus grew / measurement error / methodology refinement).
- **Reference:** the SHA-pinned record or run that supports the correction.
```

*No corrections to the make-or-break gates have ever been needed: external metamorphic-FP has stayed **0** and the Mirror hard gate (`deepinit_wrong_high`) has stayed **0** across every measurement (see `validation/_baseline.json`).*
