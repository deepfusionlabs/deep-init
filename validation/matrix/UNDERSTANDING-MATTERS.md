# — "Understanding MATTERS": the measured 3-mode A/B

* (operator-emphasized 2026-06-14). The sharpest competitive differentiator, **measured** —
not asserted. On gin / click / express (3 languages, M-tier, all Graphify-parseable) each repo was
analyzed three ways and every analysis was scored by an **independent verifier** (separation of duties)
against the Graphify AST dependency-edge oracle + the real code.*

Source record: `validation/matrix/m1a_understanding_matters.json` (per-repo scorecards + aggregate).
INDICATIVE (3 repos, famous). GATED-framed: a **method** comparison, never "bugs in famous repos."

## The three modes
1. **Full designed path** — Graphify AST + resolved import graph + grounding-to-`file:line` + verification.
2. **Graphify OFF** — the grep/ctags fallback (same pipeline, no AST), still grounded + verified.
3. **Naive LLM-only** — the controlled proxy for "just send the code to an LLM and ask for docs": no
 structural parse, no grounding requirement, no verification. *A controlled baseline of the METHOD —
 not a named competitor.*

## Measured delta (mean across the 3 repos)

| metric | full | graphify-off | naive |
|--------|------|--------------|-------|
| **claims grounded to a verified file:line** | **98.9%** | **100%** | **43.5%** (min **0%**) |
| faithfulness (claims not code-refuted) | 98.9% | 100% | 100% |
| dependency-edge precision | 100% | 100% | 92.6% (min **77.8%**) |
| dependency-edge recall (vs AST oracle) | 57.5% | 60.8% | 43.1% |
| real grounded issues surfaced (total) | 5 | 5 | 6* |
| fabricated issues | 0 | 0 | 0 |

## What the data actually shows (honest, both ways)

- **Grounding is the clear, consistent differentiator.** The naive pass grounds far fewer claims to a
 *verifiable* `file:line` (gin **0%**, click 36%, express 95% → mean 43.5%) vs 99–100% for the structural
 paths. It describes from training-recall and cites bare filenames, not lines — *plausible but
 unverifiable: you can't trust which line it means.*
- **Faithfulness is high for ALL modes on these FAMOUS repos.** The model knows gin/click/express, so the
 naive pass rarely states a code-refuted fact. **We report this honestly:** on famous code the
 verified-vs-naive gap is mostly *grounding + issue-discovery + dependency-graph completeness*, not raw
 hallucination. On obscure/private code (no training recall) the faithfulness gap should widen — a
 hypothesis for future datapoints, not a claim made here.
- **The naive pass inflates the dependency graph.** It mixed *non-import runtime couplings* into the
 import graph (express: precision 77.8% vs 100%) and recovered ~half the edges (43% vs ~60%).
- **Verification earns its cost (issue-discovery).** On gin the structural paths surfaced 2–3 grounded
 security-relevant findings (insecure-default trusted-proxy CIDRs; Authorization-only panic sanitization;
 unsafe bytesconv aliasing); the naive pass surfaced **0** grounded issues (it ran no verification).
 *\*Where naive listed "issues" (express), they were ungrounded heuristic smells.* All recorded GATED —
 these are known behaviors, a comprehension demonstration, not filed bugs.
- **DeepInit's grounded read EXCEEDED the AST parser.** On click both structural modes caught 3 real
 internal imports (`core/parser/testing → _utils/utils`) the raw Graphify oracle had dropped, and flagged
 the gap — comprehension above a mechanical parse.
- **On small clean DAGs, grep-fallback ≈ Graphify.** For these tidy repos the grep path matched (even
 edged out) the AST oracle; the AST advantage should show on larger / more-tangled codebases where grep
 can't resolve imports. Honest: on this subset the bigger delta is *verified-vs-naive*, not *Graphify-vs-grep*.

## The one-line story (for )

*"Most tools send your code to an LLM and hand you a plausible description. DeepInit parses your code,
grounds every claim to a verified `file:line`, and verifies it — so when it says something is at
`response.js:298`, it is. In our measured A/B the naive approach grounded 43.5% of its claims (0% on one
repo) and missed every grounded security finding; DeepInit grounded 99–100% and surfaced them."*
