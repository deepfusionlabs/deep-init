<!-- DEEPINIT:HUMAN-AUTHORED — not a DeepInit-managed region -->
# DeepInit in the Wild — validation evidence

This folder holds the **openable, reproducible evidence** behind DeepInit's precision/cost/recall
claims: structured per-repo records from running DeepInit's detectors against **real, pinned OSS
repositories**. It is the auditable backing for the "How we tested it" story on the product page —
every number here resolves to a `repo@SHA` + a `file:line`.

It complements, not replaces, the two existing evidence layers:

| Layer | What | Where |
|-------|------|-------|
| Deterministic harness | 141 no-LLM regression/oracle checks (toposort, cost, the issue oracles, census math, SARIF, blind-run recall/FP scoring, **and §32 — the precision gate over the records below**) | [`tests-fixtures-v1/_chat_validation.py`](../tests-fixtures-v1/_chat_validation.py) |
| Test-plan runbook + Run log | the reproducible commands + the measured-run history (blind recall/FP, the external metamorphic oracle) | [`docs/deepinit-evolution-test-plan.md`](../docs/deepinit-evolution-test-plan.md) |
| **This folder** | **per-repo, repo@SHA-pinned records from real-world runs** | `validation/results/*.json` |

## The program

"DeepInit in the Wild" instruments real OSS repos across three tracks. See the program plan in
[`docs/deepinit--plan.md`](../docs/deepinit--plan.md) (the "DeepInit in the Wild" phase)
and the run-record schema in [`docs/reference/deepinit-instrumentation-schema.md`](../docs/reference/deepinit-instrumentation-schema.md).

- ** — precision.** A *naive* "structural-mismatch = violation" detector vs DeepInit's
 *guarded* detector + census overlay, on repos carrying a documented class-ranging rule. The metric
 is **naive false-positives avoided** and **false defects emitted** (must be 0). This is where the
 `results/` records below live — and harness **§32** gates them deterministically (arithmetic-consistency
 for CORROBORATE/STALE, a named `degrade_guard` for any DEGRADE that diverges from the bare arithmetic,
 `naive_fp == N−k`, zero false defects; RED-confirmed load-bearing).
- ** — cost/usage** ([`cost/`](cost/)). Full skill-runs across size tiers → a cost/usage
 estimate model for the product page (time, tokens, est-$). All `$` figures are **labeled
 estimates** (token counts × public list price at a stated date), never billed figures. The ledger
 schema is **enforced** by harness §33.
- ** — recall/discovery** ([`recall-discovery/`](recall-discovery/)). Recall via the external
 metamorphic bugfix-pair oracle (the live number is in the test-plan, currently **14/22**,
 metamorphic-FP **0/22**), plus a gated live discovery pass for case studies (Shape-A real findings
 / Shape-B precision-silence — e.g. the kemal Crystal sweep: 0 issues, every near-candidate
 suppressed by a named guard).

## Track-1 results (, recorded 2026-06-10)

Four real repos, each carrying a documented class-ranging rule, run through the **census overlay +
guarded IF-4**. All four were **clean against their rule** — so this is a *precision / scope-honesty*
validation, not a recall one. The point: a naive detector keying on literal structural conformance
would have fired ~90 false positives; the guarded detector emitted **zero false defects** and every
census signal was arithmetically correct.

| Repo | Stack | Rule source | Census (N, k) | Signal | Naive FPs avoided | False defects |
|------|-------|-------------|---------------|--------|-------------------|---------------|
| [fossasia/visdom](results/fossasia-visdom.json) | Python/Tornado | skill-guardrail doc | 18, 13 | **CORROBORATE** | 5 | 0 |
| [kemalcr/kemal](results/kemalcr-kemal.json) | Crystal | CHANGELOG | 12, 0 | **STALE** | 12 | 0 |
| [pyccel/pyccel](results/pyccel-pyccel.json) | Python | CHANGELOG | 114, 103 | **DEGRADE** | 11 | 0 |
| [evolutionary-architecture-by-example](results/evolutionary-architecture-by-example.json) |.NET/C# DDD | formal ADR-0008 | 95, 33 | **DEGRADE** | 62 | 0 |
| **Total** | 4 stacks | — | — | — | **~90** | **0** |

Each `results/*.json` carries the full census, the naive-vs-guarded breakdown, and a verbatim honest
assessment. What each signal means:

- **CORROBORATE** (visdom) — a strong majority conforms (k ≥ ⌈2N/3⌉ and k > N−k); the deviants stand
 out structurally and *would* rank up a host fire — but here all 5 deviants are **by-design**
 unauthenticated endpoints (login handler, static CSS, error page, health probe), so the guarded
 detector raises **nothing**. CORROBORATE is an overlay signal, never an auto-finding.
- **STALE** (kemal) — the literal rule is followed by *zero* shipped handlers (k=0); a **neutral
 rule-health flag** for a human, not 12 auto-judgments. The framework conforms to the *interface*
 via `include HTTP::Handler`, not the CHANGELOG's literal `< Kemal::Handler` inheritance.
- **DEGRADE** (pyccel, eabe) — the conformance property is not a single unambiguous structural fact
 (pyccel: the literal one-base CHANGELOG rule was superseded by a 3-base runtime-enforced contract;
 eabe: a SOFT "should … unless" ADR, and static classes structurally can't be sealed). The census
 emits nothing rather than guess.

## How to reproduce

1. Clone the repo at its pinned SHA (recorded in each `results/*.json` under `repo.pinned_sha`):
 ```
 git clone <url> validation/_clones/<name> && cd validation/_clones/<name> && git checkout <sha>
 ```
 (`validation/_clones/` is gitignored — clones are bulky scratch, not committed.)
2. Locate the documented rule at the cited `file:line` (each record's `documented_rule`).
3. Enumerate the rule's class and count conformers with the census overlay's structural check
 (each record's `census.class_selector` + `census.conformance_check`).
4. Apply the census thresholds — CORROBORATE `k ≥ ⌈2N/3⌉ ∧ k > N−k`; STALE `k ≤ ⌊N/3⌋ ∧ N ≥ 4`;
 DEGRADE `N < 3 / generated-or-ambiguous membership / non-structural property` — and confirm the
 guarded detector raises no per-site defect.

> **SHA honesty note.** The validation clones were not retained; the pinned SHAs were resolved from
> the GitHub API as each repo's default-branch HEAD *at or before the 2026-06-10 validation date*.
> The durable anchors are the `file:line` citations, which are SHA-robust here because they describe
> structural conformance to slow-changing documented rules. Future instrumented runs pin the SHA at
> clone time (see the instrumentation schema).

## Honesty guardrails (every record obeys these)

- DeepInit measures its **own** false-positive rate; it never quotes a vendor number.
- "Naive FPs avoided" counts what a *literal-conformance* detector would have fired — it is a
 precision contrast, not a claim that those sites are bugs (they aren't; the repos are clean).
- These four repos are a **scope-honesty / precision** sample (all clean against their rule); they
 do **not** measure recall. Recall lives in the test-plan's external metamorphic oracle.
- Cost figures (, when added) are labeled estimates with a stated method and date.
