<!-- DEEPINIT:HUMAN-AUTHORED — not a DeepInit-managed region -->
# The Mirror Test — core-output coverage records

Validation evidence for DeepInit's **core output** (the architecture map / component registry /
dependency edges / data-flow / persistence facts / key non-obvious facts it writes into `CLAUDE.md`
+ `.ai/docs/`) — measured as **AGREEMENT (coverage + faithfulness)** against a project's own
reliable, code-current reference doc.

Across **4 held-out / tune stacks** — **eabe** (.NET/ADRs), **helix** (Rust/ARCHITECTURE.md),
**scrapy** (Python/architecture.rst), **otelcol** (Go/internal-architecture.md): **pooled held-out
doc-coverage 71/88 = 80.7%** (Wilson95 LB 71%), **faithfulness 72/75 = 96%**, the one hard gate
**`deepinit_wrong_high` Σ = 0**, 359 beyond-doc. Strong on structure (component-role 100%, data-store
100%, entry-point 100%, component-exists 92%), weakest on key-invariants (22%) — a gap a later generic
skill fix lifted (helix 71%→90%, key-invariant 0/6→5/6; faithfulness →100%; hard gate 0).
INDICATIVE — the §18 blind-fixture result (9/9, FP 0) stays the headline.

## Layout

| Path | Holds |
|------|-------|
| `_blind_artifacts/<repo>/` | the BLIND DeepInit output (`AGENTS.md` + `.ai/docs/`) — independently re-derived from the doc-removed code, `doc_in_inputs==false` |
| `results/<repo>.json` | the scorer's `coverage-record/v1` (the buckets, the per-kind coverage vector, faithfulness, the one hard gate) — §34-gated |
| `_pooled_m4_summary.txt` | the pooled held-out per-kind coverage + faithfulness vector + the MISS taxonomy across all repos |
| `_m5_postfix/<repo>.json` | the skill-fix held-out re-validation records (post-fix re-score vs the same frozen keys; outside `results/` so §34 does not gate them) |

## The non-negotiables (from the protocol)

- **AGREEMENT, not divergence** — a "doc says X, code does Y → flag" detector is OUT of scope.
- **Currency is VERIFIED** — every Reference Claim is code-checked at the pinned SHA; stale ones are dropped *before* scoring (the firewall), never counted against DeepInit.
- **The firewall** — `provenance.doc_in_inputs == false` on every engine artifact (the product run never saw the doc). The held-out reference keys are kept out of this published set, so a model can't memorize them and the anti-contamination claim stays honest.
- **Indicative, not gated** — coverage% / faithfulness% are reported with a Wilson95 LB + caveats; **§18 (9/9, FP 0) stays the product headline**. The ONE hard gate is `deepinit-wrong-HIGH == 0`.
- **No overfitting** — a frozen TUNE / HELD-OUT split; the held-out set is scored once.

No cost ledger lives here (that is `validation/cost/`); no issue-layer precision record lives here
(that is `validation/results/`). This folder is core-output coverage only.
