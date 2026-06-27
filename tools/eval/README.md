# `tools/eval/` — DeepInit evaluation harness

A reusable **Capture → Score → Aggregate** pipeline for measuring DeepInit (and any comparable tool)
on a pinned repo matrix across many dimensions. Born from the DeepInit-vs-`/init` head-to-head (`m1b`);
see `docs/design/deepinit-eval-framework.md` for the
extension roadmap and `docs/design/init-head-to-head-benchmark.md`
for the methodology.

> **Status:** working scripts preserved from the first real run. They carry **hardcoded scratch paths**
> (`c:/tmp/init-bench`, the workflow-output path in `finish_*`) from that run — a future run re-points
> them. Cleanly parameterizing into a committed, harness-gated suite is Axis 5 of the framework plan.

## Pipeline
1. **Capture (metered)** — [`../run_init_benchmark.py`](../run_init_benchmark.py) drives one arm
   (`/init`, `/deep-init:fast`, …) on a pinned clone, K runs, capturing raw `CLAUDE.md` + real
   `total_cost_usd` + tokens + the deep `.ai/` tree. Env-guarded (`DEEPINIT_REAL_ENGINE=1`),
   fail-closed SHA pin, `--max-budget-usd` cap. `capture_group.sh A|B|C` batches it over a repo group.
2. **Anonymize** — `build_score_tasks.py` copies every captured `CLAUDE.md` to an opaque-labelled
   inbox (so scorers can't key off the source path) and emits `tasks.json` + `mapping.json`.
3. **Score (blind)** — `score_workflow.js` is a Workflow: one independent verifier per output, each
   reading the candidate file + the real clone and returning grounding / faithfulness / dep-edge
   recall (vs `validation/matrix/oracles/`) / depth-by-fact-kind / issues real-vs-fabricated /
   wrong-HIGH / actionability. Separation of duties: curator ≠ scorer ≠ author.
4. **Aggregate** — `build_m1b_record.py` (quality, by arm/fame/repo), `build_instrumentation.py`
   (cost/tokens/footprint by size tier), `build_analytics.py` (fact-kind, determinism, issue
   precision, faithfulness-by-fame, per-language, value-per-dollar).

## Records produced (committed evidence — R1: every figure traces to a raw file)
- `validation/matrix/m1b_init_head_to_head.json` — the quality head-to-head.
- `validation/matrix/m1b_instrumentation.json` — real api_usage cost/token/footprint model.
- `validation/matrix/m1b_analytics.json` — the deeper cross-cuts.
- `validation/matrix/init-outputs/<repo>/{init,deepinit}/run-*/CLAUDE.md` (+ deepinit `.ai/`) — raw.

## First run — headline (9 repos · 8 languages · S/M/L · 36 blind-scored outputs)
| | `/init` | DeepInit (`fast`) |
|---|---|---|
| grounding (verifiable `file:line`) | 0.6% | 77.6% |
| faithfulness | 98.3% | 97.9% |
| wrong-HIGH | 13 | 5 |
| actionability (1–5) | 4.1 | 4.9 |
| cost/run (api_usage) | $0.90 | $4.40 (4.5–5.1×) |

## Caveats
- **Metered** — capture spends real money (operator-gated, `DEEPINIT_REAL_ENGINE=1`).
- **Wall-clock is invalid here** — groups ran in parallel; timing needs isolated (non-parallel) capture.
- **Publishable: indicative** until a clean isolated run + held-out/post-cutoff repos (training-
  contamination caveat: on famous repos both arms are ~98% faithful — grounding is the differentiator).
- The cloned test repos are **reproducible from the pinned SHAs** in `validation/matrix/_manifest.json`
  (not committed; re-clone on demand).
