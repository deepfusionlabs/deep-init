# validation/graphify — the designed Layer-3 path, wired + A/B-validated

**,.** DeepInit is *designed* and *advertised* to parse code via
[Graphify](https://github.com/safishamsi/graphify) (detection.md Layer 3, spec §9, the cost
`graphify_discount`, the product-page hero) — but until now every validation (the 15 field
sweeps, the Mirror Test, the kemal cost ledger) ran on the **grep/ctags fallback**, never the
designed path. This folder closes that fidelity gap.

## What's here
- **`ab-graphify-vs-fallback.json`** — the A/B record (`graphify-ab-record/v1`): Graphify designed-path
 vs the committed grep-fallback findings, on excalidraw (TS), pyccel (Python), kemal (Crystal), with
 every claim verified against the real source at a pinned SHA.

## How the path works
1. `graphify update <repo-or-component> --no-cluster` → `<path>/graphify-out/graph.json`
 (deterministic tree-sitter AST extraction — **no LLM, no API key**). The real CLI is `update`,
 **not** the `graphify extract` detection.md previously assumed (reconciled).
2. `python tools/graphify_adapter.py --graph <…>/graph.json --registry <registry.json> --out structural-graph.json`
 maps the `{nodes,links}` graph to the component-keyed `structural-graph.json` the detectors consume
 (resolves each import to its **defining component**, drops intra-component edges, separates external
 deps, exposes a Tarjan SCC for the IF-8 substrate). Gated by **harness §35** (the `mini-graphify` fixture).

## The headline finding (honest)
- **Graphify RESOLVES imports the grep fallback can only string-match** — it follows scoped package
 aliases (`@excalidraw/utils/shape` → `packages/utils/src/shape.ts`) and re-exports, so the
 dependency-edge / IF-8 / IF-3a skeleton is materially more accurate on the **14** tree-sitter
 languages (C, C#, C++, Groovy, Java, JS, Kotlin, Lua, PHP, Python, Ruby, Scala, Swift, TS).
- **It independently CONFIRMS** the gated excalidraw element↔utils runtime cycle (a different mechanism
 than the grep that found it — a genuine cross-mechanism re-verification) and **surfaces** a real pyccel
 `ast↔errors` circular import the IF-10-scoped sweep didn't target.
- **It does NOT replace DeepInit's discipline.** Raw `--no-cluster` extraction doesn't tag `import type`
 vs value, so a naive whole-graph SCC over-reports cycles on TS/Java — the IF-8 type-vs-value suppression
 and the "main-loop double-verify every fire" rule stay load-bearing. Consistent with precision-first.
- **No grammar = graceful fallback.** 5 of the 15 swept stacks (Crystal, Go, Rust, Elixir, OCaml) have no
 Graphify grammar; those fall through to ctags/grep automatically (global-rules R8), never crash or fabricate.

## Reproduce
```bash
graphify update validation/_clones/excalidraw/packages --no-cluster
python tools/graphify_adapter.py \
 --graph validation/_clones/excalidraw/packages/graphify-out/graph.json \
 --registry <a {component:[path]} map> --cycles --out /tmp/sg.json
```
The `graphify-out/` outputs are NOT committed (large, regenerable); the A/B record carries the verified conclusions.
