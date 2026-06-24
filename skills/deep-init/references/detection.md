# detection.md — C1 Detector (+ planning inputs)

Maps the project, detects architecture, builds the component registry, extracts git intelligence, detects databases, and estimates cost. All deterministic — runs **before** any LLM tokens are spent. Output: `.ai/docs/current/discovery.md` + `structural-graph.json`.

## The layered ladder (R6)
Each layer is additive (~0 tokens through Layer 6); skip any that's unavailable and continue. Tag each file `[GRAPHIFY] > [CTAGS] > [GREP] > [LLM-ONLY]`.

1. **Directory & manifest** (always) — file list/sizes/types via `find`/`ls`; dependencies from `Gemfile`, `package.json`, `requirements.txt`, `go.mod`, `*.csproj`, `pom.xml`.
2. **Metrics — scc** (if installed) — `scc --format json .` → LOC, complexity, language breakdown per component.
3. **Structural skeleton — Graphify** (installed by default; `pip install graphifyy`, no API key for AST extraction) — `graphify update <repo-or-component-path> --no-cluster` → deterministic tree-sitter AST extraction (no LLM) → `<path>/graphify-out/graph.json` (a `{nodes[], links[]}` code graph). Run the **`graph.json → structural-graph.json` adapter** (`tools/graphify_adapter.py`, see below) to get the component-keyed skeleton DeepInit consumes. **Operational notes (from dogfooding):** (a) the working CLI is the `graphify` console-script — on Windows it lands as `graphify.exe` in the Python **`Scripts/` dir, often NOT on PATH** (invoke by full path or add Scripts/ to PATH); a same-prefix **`graphify-mcp`** binary also ships and takes DIFFERENT args (the MCP server) — do not confuse them. (b) **`graphify update` is NOT read-only** — it writes `graphify-out/` (graph.json + a cache) INTO the scanned dir, defaulting to the path root. On a run that must leave the target pristine (a clone you'll re-use, a repo you don't own), run Graphify against a **copy**, or move/remove `graphify-out/` afterward, and KEEP `graphify-out/` in the exclusion pass's always-skip set so a subsequent scc/scan never re-reads it (a stray `graphify-out/graph.json` otherwise mis-counts the repo as huge JSON — observed). **25 tree-sitter language grammars** ship in the pinned version (0.8.39) — C, C#, C++, Go, Rust, Java, JavaScript, TypeScript, Python, Ruby, PHP, Kotlin, Scala, Swift, Elixir, Lua, Julia, Zig, Groovy, Objective-C, Pascal, Fortran, Verilog, PowerShell, DreamMaker (+ JSON/SQL/Terraform config-data grammars, and Dart/Astro/Svelte/Apex/Razor via dedicated extractors). *Empirically verified* extracting Go, Rust, Elixir, Python, TS, Java, C#, Kotlin, Swift, Scala, Julia, Zig. Stacks with **no** Graphify grammar — notably **Crystal** and **OCaml** — fall through to Layer 4/5 (ctags/grep) automatically. Falls back per-file to Layer 4 on any parse failure. **Shell/Bash `.sh` files DO parse** (verified, not assumed) — a dogfood run on a shell-heavy plugin repo produced 156 function-level AST nodes from `scripts/*.sh` (`source` resolves as import edges), so a Shell-heavy repo is NOT pre-judged fallback-only; raw `--no-cluster` does leave variable-interpolated `source "$DIR/x.sh"` paths as synthetic var nodes, so supplement with a grep of `source` statements to resolve those file→file edges.
4. **Symbol index — universal-ctags** (if installed) — `ctags -R --output-format=json --fields=+n .` → symbol + `file:line`. Used if Graphify unavailable or as supplement.
5. **Pattern scan — grep/ripgrep** (always) — tech-stack patterns (see Import Patterns below + def/class/route/validation/association greps per language); universal tech-debt signals: `grep -rn "TODO\|FIXME\|HACK\|XXX\|DEPRECATED\|workaround\|temporary"`.
6. **LSP** (if configured, optional) — `findReferences`/`goToDefinition`. **Known fragile in Claude Code** (#14803/#20050/#21335) — supplement only, never the sole source.
7. **LLM semantic analysis** (token-consuming) — reads file content WITH all structural context from Layers 1–6. This is the only token-spending layer; better inputs → better output. (Lives in `extraction.md`.)

## Exclusion pass (deterministic — runs BEFORE every layer)
Scanning the wrong files wastes tokens AND pollutes the structural graph (Graphify will happily parse a vendored bundle or a `*.json` fixture as if it were first-party code — observed in Track-0 validation). Build the candidate file set ONCE, deterministically, and feed the SAME filtered set to every layer (scc, Graphify, ctags, grep):
- **Honor `.gitignore`** — prefer `git ls-files` (respects `.gitignore` + `.git/info/exclude`) as the file source on a git repo; fall back to a `find` with the default-excludes below when not a git repo.
- **Always-skip directories** (case-insensitive, any depth): `node_modules`, `vendor`, `bower_components`, `dist`, `build`, `out`, `target`, `.next`, `.nuxt`, `.svelte-kit`, `coverage`, `__pycache__`, `.venv`/`venv`, `.tox`, `.mypy_cache`, `.pytest_cache`, `.gradle`, `.idea`, `.vscode`, `.git`, `.deepinit`/`.ai`, `graphify-out`, `.terraform`, `Pods`, `DerivedData`.
- **Skip generated / vendored / minified files**: `*.min.js`/`*.min.css`, `*.map`, lockfiles (`package-lock.json`, `yarn.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`, `composer.lock`), `*.generated.*`/`*_pb2.py`/`*.pb.go`/`*_generated.go`, snapshot/fixture data (`__snapshots__/`, `*.snap`), and files whose header marks them generated (`@generated`, `Code generated … DO NOT EDIT`, `Auto-generated`).
- **Skip binaries / non-source by extension**: images, fonts, archives, media, `*.pdf`, `*.lock`, `*.bin`, `*.wasm`, compiled artifacts.
- **Skip over-size files** (default **> 1 MB** or **> ~20k lines**) — log each as `[SKIPPED:oversize file:bytes]`; never silently drop.
- **Monorepo scoping** — if `packages/*/`, `apps/*/`, or workspace manifests are detected and the run is component-scoped, restrict the candidate set to the in-scope package(s); record the scoping in `discovery.md §8`.
- **Honesty**: every exclusion is COUNTED and the totals (`{gitignored, vendored, generated, binary, oversize, out_of_scope}`) go into `discovery.md §8` (Structural Analysis Status) and the `extraction_ladder.skipped` field — a silent skip reads as "analyzed and clean" when it wasn't (global-rules R8). Data/config files Graphify *can* parse (e.g. a `*.json` fixture) are excluded from the **component/edge** skeleton even when kept for tech-stack detection.

## `structural-graph.json`
Built from Graphify output (or a rough grep-import graph if Graphify is absent):
```json
{
  "version": 1, "source": "graphify",
  "components": {
    "auth": {
      "files": ["app/models/user.rb", "app/controllers/auth_controller.rb"],
      "exports": ["User", "authenticate!", "current_user"],
      "imports_from": {"shared": ["ApplicationRecord"]},
      "imported_by": {"billing": ["current_user"], "reports": ["User"]}
    }
  }
}
```
Build via the adapter `tools/graphify_adapter.py` (the deterministic, tested reference implementation of this mapping — runnable as `python tools/graphify_adapter.py --graph <path>/graphify-out/graph.json --registry <registry.json> --out structural-graph.json`), or follow the same algorithm inline:
- **Read `graph.json`** — `nodes[]` (`{id, label, source_file, source_location}`) + `links[]` (`{source, target, relation, context, …}`). The import edges are `links` with **`context == "import"`** (relations `imports` = symbol-level, `imports_from` = module-level). A `calls` relation marks a runtime use (a value, not an erased type) — useful for the IF-8 type-vs-value distinction below.
- **Map each `source_file` to a component** (longest-prefix match against the registry; non-source/manifest files map to nothing and are excluded).
- **Resolve each import edge:** the `target` either **is a node** (→ that node's `source_file` → its component: an *internal* edge) or **is not a node** (→ an *external* third-party package). A cross-component edge (src-comp ≠ tgt-comp) becomes `imports_from`/`imported_by` carrying the imported symbol; the imported-across-a-boundary symbol is added to the target's `exports` (its public surface). Intra-component edges are dropped.
- **Output** the sorted, byte-stable `components{}` map (+ an `external_dependencies{}` roll-up).

**Graphify's edge fidelity vs the grep fallback (measured, Phase-6 Track-0 A/B):** Graphify *resolves* an import to the **defining file** (e.g. it follows `@excalidraw/utils/shape` → `packages/utils/src/shape.ts`), which the grep fallback cannot — grep only string-matches the import line, so it cannot tell which component a symbol actually lives in. This makes the dependency-edge / IF-8 / IF-3a skeleton materially more accurate on the ~14 Graphify-parseable stacks. **Caveat (carry into IF-8):** Graphify's raw `--no-cluster` extraction does **not** tag `import type` vs value imports, so a naive whole-graph SCC over the adapter's edges over-reports cycles on TS/Java (compile-erased type-only imports inflate the SCC). The **type-vs-value suppression stays an IF-8 skill-layer responsibility** (`issues.md` IF-8 already specifies it) — use the `calls` relation as a positive runtime-use signal when distinguishing a real runtime cycle from a type-only one.

If Graphify absent (or the stack has no Graphify grammar): skip, note "Structural graph: unavailable for these files (install Graphify / no grammar for <lang>) — using grep-inferred imports", and Extract uses grep-inferred imports (the ~80% approximation that cannot resolve a symbol to its defining file).

## Import-pattern detection (grep fallback for the dependency graph)
When Graphify is unavailable, build a rough graph from imports (~80% of cross-component imports):
```bash
# Ruby     grep -rn "require\|require_relative\|include \|extend " --include="*.rb" .
#          (Rails/Zeitwerk autoloads → few explicit imports; supplement with class refs, belongs_to/has_many, before_action)
# Python   grep -rn "^import \|^from .* import " --include="*.py" .
# TS/JS    grep -rn "import .* from \|require(" --include="*.ts" --include="*.tsx" --include="*.js" .
# Go       grep -rn "^import " --include="*.go" .
# Java     grep -rn "^import " --include="*.java" .
# C#       grep -rn "^using " --include="*.cs" .
# Rust     grep -rn "^use \|^mod " --include="*.rs" .
# PHP      grep -rn "^use \|require_once\|include_once" --include="*.php" .
# Elixir   grep -rn "^import \|^alias \|^use " --include="*.ex" --include="*.exs" .
```
Map each import to a component (longest-prefix). Cross-component imports become edges.

## Architecture detection (3-tier adaptive)
**Priority 0 — DeepMap / Graphify prior:** if `.deepmap/community_summaries.md` exists, use its subsystem groupings AS the component registry (skip Priority 2 heuristics) — empirically-derived structure. Also check `graphify-out/`, `structural-graph.json`.
**Priority 1 — explicit docs:** `ls docs/architecture* ARCHITECTURE* .ai/docs/`; `cat CLAUDE.md AGENTS.md | head -50`. If architecture is documented, use it.

### Existing agent-file reconcile (B3 — detect the case for the emitter)
While reading Priority-1 docs, **record which agent files already exist** so the emitter reconciles them instead of orphaning a second file. `CLAUDE.md` is the canonical lean tier (Claude Code auto-loads it; it does NOT read `AGENTS.md` natively — `generation.md` *The canonical lean tier*). Probe the repo root for `CLAUDE.md` and `AGENTS.md` and classify into one of **four cases**, recorded in `discovery.md`:
- **only-CLAUDE.md** (CLAUDE.md present, AGENTS.md absent) — the emitter's grounded lean tier BECOMES `CLAUDE.md` (owns the front door); the EXACT prior file → the dated `.bak`, its genuinely-always-needed human directives carried forward into the human-owned region, the rest of its prose relocated to `.ai/docs/`. **Flag a heavy `CLAUDE.md` (> ~200 lines, Claude Code's own guidance) — its bulk is exactly what relocates to the deep tier; never delete, archive + relocate.**
- **only-AGENTS.md** (AGENTS.md present, CLAUDE.md absent) — reconcile to `CLAUDE.md` as canonical (the Claude-Code-native tier); keep the lean `AGENTS.md` as the cross-tool export.
- **both** — `CLAUDE.md` is canonical; keep `AGENTS.md` as the lean cross-tool export (deduped — one lean tier).
- **neither** — emit `CLAUDE.md`; add the `AGENTS.md` cross-tool export only if a cross-tool consumer is detected (below).
Also note any DeepInit owned-region markers already present (a prior run) vs a foreign/human-authored body (carried-forward + the dated `.bak` preserve it). The reconcile ACTION lives in `generation.md`; detection only records the case + whether each file is human-authored. *(`--canonical=agents` inverts the canonical/export roles — see `generation.md`.)*

**Cross-tool consumer detection (the conditional `AGENTS.md` export, B4-adjacent).** Also record which cross-tool consumers are present so the emitter knows whether to emit the cross-tool `AGENTS.md` export + projections (a Claude-Code-native repo gets NO redundant root `AGENTS.md`): a **`.cursor/`** dir (Cursor) · **`.github/copilot-instructions.md`** (Copilot) · a **`.windsurf/`** dir or `.windsurfrules` (Windsurf). Present (or an explicit `--emit-agents` / `--canonical=agents`) → `emit_agents_export = true`; absent → the export is skipped and that is stated in the run summary.
**Priority 2 — directory heuristics:**

| Signal | Architecture |
|--------|-------------|
| domain/ + infrastructure/ + application/ | Clean Architecture |
| controllers/ + services/ + models/ | Layered |
| features/*/ with internal structure | Vertical Slices |
| adapters/ + ports/ | Hexagonal |
| packages/*/ or apps/*/ with own manifests | Monorepo |
| app/controllers + app/models + app/views | MVC (Rails/Laravel/Django) |
| No clear pattern | Legacy/Organic — flag for extra care |

**MVC decomposition (critical):** decompose by **DOMAIN, not LAYER**. Don't treat `app/controllers`, `app/models`, `app/views` as components — they're layers. Instead group across layers by domain: `auth_controller` + `user` model + auth service + auth views → one `auth` component. Use controller-name groupings + subdirectories (e.g. `controllers/admin/` → `admin`) as the primary domain signal; models/services follow.
**Priority 3 — flat fallback:** each top-level dir with source files = a component.

## Component registry
Build a table; populate tests/README/file counts per component:
```markdown
| Component | Path | Type | Files | Source lines | Has Tests | Has README | Architecture |
```
Record **file count + source lines + whether the component owns its own directory** per component — these feed the emitter's objective **nested lean-file rule** (file-agnostic — the nested basename is the canonical file, `CLAUDE.md` by default; `generation.md`: ≥ 2 source files OR ≥ 200 source lines + own directory + a lean finding → emit by default; the Emit-completeness check verifies it). Without these the C7 emitter can't decide nested placement and falls back to under-emitting one root file (the B1 failure).

**Measured calibration (Phase-6 M8-Q1, 2026-06-14 — cover the TOOLING LAYER, not just code components).** A real multi-component run on excalidraw (6 components, 128 grounded facts, faithfulness 100%, 0 confidently-wrong) went FAR deeper than a single-pass read on the *code* (24 key-invariant/boundary facts on undo-redo, versioning, binding) but **under-covered the build/test/tooling layer** — Yarn workspaces, the bundler (esbuild/vite), the test runner (vitest), `tsconfig` strictness — because those live in **root config files that are not "components" in the dependency graph**, so a component-keyed extraction skips them (the single-pass proxy, reading the whole repo at once, caught them). **Fix:** the architecture-overview pass must explicitly capture the **project-level technology choices** (package manager / workspace tool, build system, test runner, language config, CI) as `technology-choice` facts in the lean tier — derive them from the root `package.json`/`pyproject.toml`/`go.mod`/`Cargo.toml`/`*.config.*` + `scripts/` + `.github/workflows/`, NOT only from the per-component source. A repo's documented architecture spans BOTH layers; cover both. (Record: `validation/end-to-end/excalidraw-real/_q1_real_engine_record.json`.)

## Git intelligence
Churn hotspots (6mo), recent activity (30d), bus factor (unique authors per dir), tech-debt commit-message signal (`fix|hack|workaround|hotfix|revert|temp|wip`), total commits + active period. Per-component detail → `.ai/docs/current/git-intelligence.md`. Used for `--update` prioritization (high-churn first).

**Change-coupling (NEW — feeds IF-5).** From the 6mo history, compute file pairs that **co-change** — appear together in ≥ `change_coupling_support` commits (default **3**) — and flag any co-changing pair with **no structural dependency edge** between their components (per `structural-graph.json`) as **hidden coupling**. One `git log --name-only --since=6.months` pass; cheap. This **temporal** signal is deliberately kept distinct from the **static** `imported_by` cascade (IF-5 vs IF-3a — see `issues.md`).

**History-depth preflight (robustness).** Before computing churn / bus-factor / change-coupling, probe depth: `git rev-parse --is-shallow-repository` + `git rev-list --count HEAD`. On a **shallow clone** (CI `--depth=1`) or a **young repo** (few commits / shorter than the 6mo window), the git signals are unreliable — mark every IF-5 output **`[LOW]` certainty and STATE the reduced coverage** in `discovery.md` §5; never emit a confident hotspot or a silent zero from thin history (recommend `git fetch --unshallow` for full IF-5).

**Stage-timing source (honesty).** The Detect and Plan stages emit a stage-timing stamp (see extraction.md → "Stage-timing emission"); every recorded timing figure carries its `time_source` on the honesty ladder `external_metered` › `engine_stage_stamps` › `formula_estimate`. Only an `external_metered` figure (a runner observed the wall-clock externally) is publishable; an engine self-stamp is attribution-only. This keeps the manifest `processing_metrics` + the cost ledger `cost.processing{}` honest about which numbers are measured vs self-reported.

## Database connection detection
Grep config for connection strings across stacks (Rails `config/database.yml`; Django `settings*.py`; .NET `appsettings*.json`; Node `.env`/`DATABASE_URL`/`MONGO_URI`/`REDIS_URL`/`NEO4J_URI`/`ELASTICSEARCH_URL`; `docker-compose*.yml` data services; file-based SQLite). **Multiple databases are common — detect ALL.** Identify access method per DB (MCP → CLI → none). Surface the choice as the plain **database card** of the Run-start prompt (`db_gate.db_prompt_options` — a plain y/n + a Dev/Staging/Prod env picker when several configs exist, prod auto-declined; `SKILL.md` *Run-start prompt*, `database.md`), NOT a raw list or internal terms; the user picks there. **Connecting is gated by global-rules §R7.**

## Cost estimate (preflight)
```
total_source_lines = scc LOC (or find/wc fallback)
# TWO ORTHOGONAL AXES — do not conflate (they otherwise read ambiguously):
#   --depth = file-read BREADTH:   fast (grep-first) | thorough (read all) | deep (read all + deepest per-file)
#   review mode = CYCLE COUNT:     fast 0 | thorough 2 (+ an adaptive 3rd iff the cycle-2 quality gate still fails)
# Each named profile collapses to ONE effort multiplier (so the always-shown estimate is never against an undefined tier):
effort_multiplier: fast 0.5 | thorough 1.4 | 3-cycle ceiling 1.8 | (legacy single-word default 1.0)
#   COST FORECAST uses the HEAVIEST review (the adaptive 3rd cycle → 1.8) as a conservative upper bound; the bare-run DEFAULT settles at thorough/2 (1.4) whenever the cycle-2 gate passes, so real cost ≤ forecast (a safe --max-cost ceiling). Effort is a minor term — the base is a heavily-caveated FLOOR (see calibration below).
graphify_discount: Graphify available 0.6 | else 1.0
base_tokens      = total_source_lines × 1.2 × effort_multiplier × graphify_discount

# Issue pass (FL-4) — added ONLY when --issues is on; 0 when --issues=off.
#   IF-2 / IF-5 are deterministic (consume the already-computed ORM-drift + git signals) → ~0 marginal tokens.
#   IF-1 / IF-3a / IF-4 / IF-7(a) are semantic: cost scales with COMPONENT COUNT × extracted-set size
#   (BR/IP/WF/ADR), bounded to per-component + ONE horizontal pass — NEVER all-pairs / file² (AF-3).
issue_pass_tokens = (--issues=off) ? 0
                  : Σ_components(extracted_set_lines × issue_factor, for the enabled IF-1/IF-3a/IF-4/IF-7(a)) + horizontal_pass
estimated_tokens  = base_tokens + issue_pass_tokens
```
Report: estimated tokens (**base + issue-pass shown separately**) + cost (Opus/Sonnet pricing), source lines/files/languages, component count + avg size, and which issue families are enabled. `--issues=off` zeroes the issue-pass term; `--issues-families=` narrows it.

**User-facing render (R10).** This estimate feeds the read-only panel/log, but when it exceeds the `--max-cost` spend guard the pause is presented as the plain **scope/effort card** (`SKILL.md` *Run-start prompt*) — **scale/effort first**, the dollar figure only as a secondary line labeled pay-per-use (API) — **never** as a "cost preflight / ceiling" prompt and never with raw `depth=`/`review=` tokens. The reference decision is `tools/prompt_ux.py` `cost_pause_decision()`.

**Measured calibration (Phase-6 M2, 2026-06-14 — the formula is CALIBRATED, not replaced).** Nine single-engine passes across S/M/L (`validation/matrix/COST-MODEL.md`, `tools/build_cost_model.py`) show the bare LOC-linear `base_tokens` term **UNDER-forecasts small repos badly** (itsdangerous, ~1.1k LOC: actual/base ≈ **106×**) because a real pass has a **fixed overhead floor** — reading the stage refs + reasoning + re-reads — that dominates below ~M scale; the actual/base ratio falls toward the kemal anchor (~14×) only as LOC grows. Practical reading: **a tier-S/M single-engine run lands ~150–230k tokens / ~$0.6–$1.7 (Opus-4.8 list, INDICATIVE)** regardless of exact LOC, and **component count drives cost more than raw LOC at S/M** (express @15.9k LOC / 7 components cost *less* than itsdangerous @1.1k LOC / 8 components). So: keep the LOC×1.2×effort×graphify_discount base, but treat it as a FLOOR-plus-per-component estimate, not a linear LOC predictor — add a ~120–150k-token fixed-overhead floor when reporting S/M, and lead with the per-tier ranges in `COST-MODEL.md`. (Output measured via budget delta; input estimated via the kemal in/out ratio → INDICATIVE; a *published* $ still needs a clean `api_usage` S/M/L run.)

## Selective activation (right-size the profile — over-activation is a defect too)
The bare-run default is depth=deep + review=**thorough** (2 cycles, with an adaptive 3rd when the cycle-2 quality gate still fails); the cost preflight conservatively forecasts at the heaviest effort (the 3-cycle ceiling, 1.8) as an upper bound. On a **small or trivial** target even the default is wasteful — running a heavy path on a 200-line single-file utility spends tokens for no extra insight. After the cost preflight, the Wave-0a panel **auto-suggests a lighter profile** when the target falls below these thresholds (it *suggests*, never silently downgrades — the user can override, and the suggestion is one line in the panel):
- **Tiny** (< ~1.5k source lines OR < ~15 source files OR 1 component) → suggest `--depth=fast --review=fast` (effort 0.5): "Small target — a light profile likely suffices; press enter to accept max-quality, or re-run with --depth=fast."
- **Small** (< ~8k lines OR < ~2 components) → suggest `--depth=thorough` (effort 1.4) rather than `deep`.
- **Issue-pass right-sizing:** below the Tiny threshold the semantic IF-1/IF-3a/IF-4/IF-7(a) pass adds little (few cross-component interactions) — suggest `--issues-families=IF-2,IF-5` (the ~0-token deterministic ones) or `--issues=off`.
- **Never auto-downgrade silently** — record the suggestion + the chosen profile in `discovery.md §9`; the *user's* explicit flag always wins. (Symmetry with the precision-first thesis: a tool that over-runs on trivial input is as untrustworthy as one that under-runs on real input.)

## Output: `discovery.md`
Sections: 1 Project Overview · 2 Tech Stack (+ scc breakdown) · 3 Architecture Style (confidence + method) · 4 Component Registry · 5 Git Intelligence Summary · 6 Database Connectivity · 7 Legacy Health Flags (no-tests / no-docs / high-churn / single-author components) · 8 Structural Analysis Status (Graphify avail?, structural-graph produced?) · 9 Cost Estimate.

## Robustness
Version-detect each tool; missing/unparseable output → log + fall through to the next layer (never crash). No clear component boundaries → directory heuristics → else single component.
