<!-- DEEPINIT:HUMAN-AUTHORED — not a DeepInit-managed region -->
# DeepInit in the Wild — (cost/usage) ledgers

This folder holds the **instrumentation run-record ledgers** for the cost/usage track — the
`identity` + `cost` + `coverage` instrumentation (a strict superset of the recorded-ledger schema).
Each real ledger is produced by a full `engine_proxy: full_pipeline` skill-run over a pinned `repo@SHA`.

- **`_schema-example-ledger.json`** — an **illustrative, synthetic** conformance example (NOT a
 measured run; cost numbers are placeholders, internally consistent). It exists so the schema is
 *enforced*, not just documented: harness **§33** validates it (required groups, valid enums,
 `est_usd` recomputes from its own on-record tokens × dated price, exactly one of `fixture`/`repo`
 non-null, and — when present — that any recorded forecast ratio recomputes from its own forecast terms, G9). Real
 ledgers land beside it and are gated by the same §33 (now **9 gates**).
- **`kemalcr-kemal.json`** — the **first REAL** cost ledger: a measured full-pipeline
 run over `kemalcr/kemal @b73de3d` (tier S, whole-repo) executed as a 12-subagent workflow proxy. **~1.0M tokens / est
 ~$8.25** (Opus-4.8 list $5/$25 per Mtok, **no `[1m]` premium**), **0 issues / 91 named suppressions**, census STALE. A same-day **single-engine** pass (1 agent, specs cached once) measured **~171k tokens / ~$1.28** &mdash; so the proxy inflated cost a **measured 5.9&times;**, and the true tier-S cost is the **range $1.28&ndash;$8.25** (`cost.single_engine` + `cost.est_usd_range`; §33 G4 recompute-gates both).
 `publishable=indicative` — the multi-subagent proxy re-loads the skill specs per stage (no cross-stage cache), so the
 measured total is a **conservative UPPER BOUND**, not a representative production cost; a *published* cost figure waits
 for a clean `token_source=api_usage` single-engine run across S/M/L. See the ledger's `_note` for the full method +
 caveats (and `forecast_vs_actual_ratio` 25.2× vs the full preflight / 83.9× vs base-tokens-alone).

**Honesty:** every `$`/token/time figure is a **labeled estimate** — `cost_basis =
"estimate_list_price"`, tokens × the public list price for the exact runtime model id (incl. the
`[1m]` long-context tier) at a stated `price_as_of_date`, presented as a **range**, never a billed
number or a guarantee. `wall_time_sec` is indicative-only; the cost story leads with tokens.
