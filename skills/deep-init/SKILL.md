---
name: deep-init
description: >-
  Generate an agent-agnostic, two-tier context layer for a codebase — a lean,
  always-loaded CLAUDE.md plus a deep, on-demand .ai/docs/ layer (business rules,
  live DB schema + ORM drift, cross-component workflows, and the WHY: ADRs + a
  knowledge log), every claim grounded to file:line and verified to exist.
  Built for legacy / under-documented repos. Invoke for: "deep-init", "/deep-init",
  "generate AGENTS.md / agent context", "document this codebase for an agent",
  "update the agent docs", "lint doc staleness".
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - LS
  - Bash
  - Task
  - Write
  - Edit
  - AskUserQuestion
---

# DeepInit v2.0

DeepInit gives a coding agent **grounded, verified truth about a codebase — and the real problems hiding in it** — every claim tied to a `file:line` and checked to exist. Generating the agent-context layer is the **mechanism**; the payload is trustworthy understanding plus a ranked, grounded list of actual issues (DB-vs-code drift, intent/decision contradictions, silent cross-component coupling, unenforced business rules, risk hotspots).

It emits a **two-tier** context layer:
- **Lean, always-loaded** — `CLAUDE.md` (root + nested), ~100–150 lines, ONLY the highest-value non-obvious facts. Claude Code auto-loads `CLAUDE.md` (it does NOT read `AGENTS.md` natively); **DeepInit owns this front door** — the grounded, verified replacement for `/init`. `AGENTS.md` is a **conditional cross-tool export** (Cursor/Copilot/Windsurf, or `--canonical=agents`).
- **Deep, on-demand** — `.ai/docs/` (per-component + six whole-system docs + decisions + DB + the issue ledger), comprehensive, uncapped.

Why two tiers: comprehensive *always-loaded* context **hurts** coding agents (it duplicates what they already read — ETH/LogicStar, Feb 2026); context helps only when minimal and non-obvious. So leanness applies to the loaded slice; depth is preserved on demand. **Quality is primary — leanness serves it and never trades against it.** Issues are **report-only** and **never enter the lean tier** — they live in the deep ledger, the dashboard, and SARIF.

## Pipeline (the stages, each in `references/`)
```
Detect → Plan → Extract → [Review*] → (ADR/KL) → Filter → Redact → Verify → Emit
                                   └─ Issue pass (report-only): detect → C-RAISE → verify → baseline-diff ─┘
```
| Stage | Reference | Role |
|-------|-----------|------|
| Detect (C1) | `detection.md` | layered ladder, architecture, component registry, git-intel (+ change-coupling), DB detect, cost |
| Plan (C2) | `detection.md` (cost preflight) + `extraction.md` (dependency ordering) | toposort/waves (`extraction.md`), cost preflight (base + issue-pass terms) |
| Extract (C3) | `extraction.md` (+ `database.md`) | per-component 11-section analysis; live schema + ORM drift |
| Review* | `review.md` | `thorough`=2 cycles + an adaptive 3rd iff the cycle-2 quality gate still fails; `fast`=0 (mode-gated); R1.5 back-to-code validate |
| ADR/KL | `adr.md` | the WHY — decisions + knowledge log (IF-4's input) |
| **Issue detect** | `issues.md` | IF-1…IF-5 + the shipped roadmap families IF-8 / IF-3b / IF-7 (c-slice + a-commission semantic) / IF-6 / IF-10 (IF-9 deferred); issue-record schema; baseline match-key primitive |
| **Issue raise (C-RAISE)** | `issue-filter.md` | linter-suppress · root-cause dedup · severity · polarity-flip suppression · forced R1.5 · verify routing |
| Filter (C4) | `filter.md` | non-obviousness — decides lean vs deep PLACEMENT (never deletes; issues never lean — R9) |
| Redact (C5) | `redaction.md` | secret/PII gate (unconditional; covers the issue ledger + dashboard blob) |
| Verify (C6) | `verification.md` | citation-existence + plausibility (mandatory; routes issue verification) |
| Emit (C7) | `generation.md` | two-tier output, manifest (schema 5 — +IF-5 risk metrics + processing timing), changelog, hashes, SARIF, multi-agent projections |
| **Dashboard** | `dashboard.md` | self-contained `.ai/dashboard.html` over grounded truth + issue ledger |
| **Viewer** | `viewer.md` | self-contained `.ai/docs-viewer.html` — a browsable READER over the generated docs (the human-facing first impression; a docs reader, not a graph) |
| **Report** | `report.md` | unified self-contained `.ai/report.html` — MERGES Docs (the viewer) + Insights (the dashboard) into one co-branded artifact (ADR-019); deterministic `tools/build_report.py`; vendored libs inlined, not CDN; supersedes Dashboard + Viewer |
| Update (C8) | `update.md` | `--update` (DP-1 skip + issue lifecycle) / `--lint` (0 tokens) |
| **Triggers** | `triggers.md` | notify / session-start / opt-in auto-update; the `deepinit_status.py` keystone + `setup-hooks` |
| **Heal** | `heal.md` | governed upkeep over update/lint; DEFAULT preview; hardcoded report-only floor |
| Cross-cutting | `horizontal.md` | six whole-system docs (always re-run on `--update`) |
| (all stages) | `global-rules.md` | never-fabricate, ID system (+ `ISS-`), provenance, DB security, R9 placement |

**Always read `references/global-rules.md` first.** Read each stage's reference before entering it (progressive disclosure).

## Commands
```
deep-init                              # full run — strong defaults (deep + adaptive review + issues/dashboard/SARIF on)
deep-init fast                         # skip review (0 cycles) + token-saving heuristics (= /deep-init:fast)
deep-init --update [--review]          # incremental: changed components + DP-1 propagation (+ issue lifecycle diff)
deep-init --lint                       # staleness audit, ZERO LLM tokens (+ candidate resolved/critical issues)
deep-init --status                     # deterministic staleness check (0 tokens, no LLM) — the deepinit_status.py keystone (triggers.md)
deep-init --horizontal | --horizontal-only
deep-init --decisions-only             # extract/refresh ADRs + KL only (~5 min)
deep-init --update-adr [--recheck=adr,rules,issues]   # re-check ADRs (+ BRs + open issues) vs current code
deep-init --heal[=detect|preview|apply|auto]          # govern lifecycle/citation upkeep — DEFAULT preview, report-only floor (`heal.md`)
deep-init --interactive | --wizard     # opt into the type-safe Customize picker (AskUserQuestion buttons; off by default)
deep-init --doctor                     # preflight tool/scope/config report, no token spend
deep-init setup-hooks                  # install the freshness triggers: deepinit_status.py + post-commit + SessionStart hook (triggers.md)
```
**Discoverable named commands (the type-safe front door).** The common actions are first-class slash commands so nobody hand-types flags — ten, in the `/` autocomplete. Each shows its **`description` + `argument-hint` inline in the menu**, so the user sees what a command does (and its options) *before* running it:

| Command | Does | Hint |
|---------|------|------|
| `/deep-init` | full run — adaptive review (2 cycles, auto-3 if not yet clean) | `[fast]` |
| `/deep-init:fast` | quick pass — 0 review cycles (= `deep-init fast`) | — |
| `/deep-init:refresh` | refresh only what changed | — |
| `/deep-init:check` | "is it still true?" — 0-token staleness + citation audit (the merged `--status` + `--lint`) | `[--status]` |
| `/deep-init:customize` | tune with **buttons** (no typing) — the AskUserQuestion picker | — |
| `/deep-init:translate` | emit the report in another language — opens a language picker (buttons) | `[<lang> \| other: …]` |
| `/deep-init:doctor` | 0-token preflight; offers `setup-hooks` | — |
| `/deep-init:help` | instant overview of every command + option, grouped + ordered by use | — |
| `/deep-init:version` | which version is actually running (loaded vs on-disk; reload if stale) | — |
| `/deep-init:plugin-update` | update DeepInit to the latest (one confirm) + guide the reload | — |

The `/` menu order is **not controllable** (no priority field; it sorts by name) — so **`/deep-init:help`** prints this list grouped and ordered by how often you'll reach for it (the importance order the raw menu can't give). The full surface is never deleted — only **routed to where it costs least to use** (the *tiered parameter model*): a high-frequency single-choice dial → its own command; a command's 1–2 options → the `argument-hint`; opt-in customization → the **Customize picker** (buttons, type-safe); the long tail → the schema-validated **`.ai/deepinit.config`** and **natural language** ("update the agent docs", "check doc staleness", "do a quick pass, skip the DB"). Every `--flag` stays valid for power users / CI.

**Strong, adaptive defaults.** A bare `deep-init` runs the deepest analysis — `--depth=deep`, **issue detection on** (all families), **dashboard on**, **SARIF on** — and the **default review mode is thorough**: 2 adversarial cycles, **with a 3rd added automatically only if the cycle-2 quality gate still fails** (unresolved CRITICAL or below-target coverage — see `review.md`). There is no scrutiny knob to choose: the default self-escalates when the work isn't clean, and stops at 2 when it is. `/deep-init:fast` is the one turn-it-down (0 cycles, quick pass). The run is non-blocking — it detects, shows one panel, and proceeds (no questions); tune further with the flags below, or `--interactive` for guided prompts. Issues remain **report-only** and never enter the lean tier (R9).
| Inline arg | Default | Effect |
|------------|---------|--------|
| `--components=a,b,c` | all | limit to listed components |
| `--depth=fast\|thorough\|deep` | **deep** | thorough/deep read ALL files (deep = deepest per-file); fast = grep-first heuristic |
| review mode (`fast\|thorough`) | **thorough** | bare-run review: `thorough`=2 cycles + an adaptive 3rd iff the cycle-2 quality gate still fails; `fast`=0 — orthogonal to `--depth` (see `detection.md` cost §) |
| `--skip-db` / `--skip-git` | analyze if present | skip DB / git |
| `--max-lines=root:N,comp:M` | root ~100 | lean budget only (deep never capped) |
| `--knowledge-log=on|off` | on | KL in lean root |
| `--include-mermaid` | off | add Mermaid diagrams |
| `--profile=code-only` | full | = `--skip-db --skip-git` |
| `--with-graphify` / `--no-graphify` | auto-detect | force install / skip Graphify |
| `--existing=skip|extend|replace|side-file` | extend | existing-file handling (extend = update DeepInit's own managed section of the file; side-file = preview beside, writes `CLAUDE.deepinit.md`, original untouched). On a heavy human-authored front-door file with no resolved strategy, the existing-file card of the Run-start prompt asks ONE plain-language confirmation — recommended = the default (`generation.md` *the one emit-time confirmation*) |
| `--emit-cursor` | auto (if `.cursor/`) | emit `.cursor/rules/*.mdc` |
| `--canonical=claude\|agents` | **claude** | the CANONICAL content-bearing lean file — `CLAUDE.md` (default, Claude-Code-native; DeepInit owns the front door) or `AGENTS.md` (advanced/niche AGENTS-first; `CLAUDE.md` becomes the thin `@AGENTS.md` import). Off the default flow + wizard (`generation.md`) |
| `--emit-agents` | auto (if cross-tool consumer) | force the conditional cross-tool `AGENTS.md` export + projections even with no `.cursor/`/Copilot/`.windsurf/` present |
| `--gitignore-agents=auto\|on\|off` | **auto** | mirror the SHARED agent file's gitignore state onto the generated `CLAUDE.md` + cross-tool export (auto); always stated in the run summary, never silent (`generation.md` B4). Redaction (R5) stays the secret guard |
| `--notify-on-commit=on|off` | **on** | post-commit prints a 0-token staleness nudge (`deepinit_status.py`; `triggers.md`) |
| `--notify-on-session-start=on|off` | **on** | the proactive **SessionStart** suggestion — when docs are stale, offers a one-click refresh via AskUserQuestion (plugin-shipped hook, 0 tokens, no install; alias `--check-on-session-start`; `triggers.md`) |
| `--auto-update=on|off` | **off** | opt-in: a **detached headless** `claude -p` runs `--update` after a *source* commit (spends tokens; **never auto-commits**; `triggers.md`) |

**Issue / heal / output flags** — detail in `issues.md` · `issue-filter.md` · `heal.md` · `dashboard.md` · `generation.md`:
| Inline arg | Default | Effect |
|------------|---------|--------|
| `--issues=on\|off` | **on** | detect issues (report-only; never enters lean tier — R9) |
| `--issues-families=IF-1,…` | all shipped (IF-1…IF-5 + IF-8 / IF-3b / IF-7 / IF-6 / IF-10; IF-9 deferred) | narrow which detectors run (zeroes the others' cost term) |
| `--issues-min-severity=low\|medium\|high` | **low** (ledger) | ledger/SARIF floor — withholds nothing by default; dashboard view defaults `medium`+ |
| `--issues-baseline=accept\|reset` | (off) | accept current open issues into `.issue_baseline.json` (write-once-per-id) / clear it |
| `--dashboard=on\|off` | **on** | emit self-contained `.ai/dashboard.html` (asserts zero off-host refs before default-on — AF-6) |
| `--viewer=on\|off` | **on** | emit self-contained `.ai/docs-viewer.html` — the browsable docs reader (asserts zero off-host refs + no innerHTML/eval sink before default-on — AF-6/§43) |
| `--sarif=on\|off` | **on** | emit `.ai/deepinit.sarif` (semantic families → `note`/`warning`; `partialFingerprints` = baseline key) |
| `--translate=<lang>` | (off) | also emit a translated `report.<lang>.html` (`es\|he` shipped, or `other:<language>` for any other — chrome→English); English `report.html` stays canonical. Post-generation overlay — `/deep-init:translate` opens the picker (`i18n.md`, *Translate picker*) |
| `--heal[=detect\|preview\|apply\|auto]` | preview | governed upkeep over `--update`/`--lint`; **report-only floor hardcoded** (`heal.md`) |
| `--heal-confidence=N` | (mode floor) | raise the bar before `auto` acts (loop-stability) |
| `--recheck=adr,rules,issues` | adr | widen `--update-adr` recheck to BRs + open issues over the DP-1 blast radius |
| `--max-cost=$X` | **$25** | a **spend guard for pay-per-use (API) billing** — a DeepInit setting, NOT a plan limit and not Anthropic-enforced. The run proceeds silently under it; above it, the plain **scope/effort card** (`Run-start prompt`) offers full-deep / lighter / narrower / cancel. On a Claude subscription you aren't billed per run, so this acts as a scale trigger only. `--yes` skips it; tune per repo |
| `--yes` / `--no-confirm` | (max-quality run is already non-blocking) | **`--yes`** (canonical) suppresses every run-start prompt card incl. the over-guard scope/effort card; `--no-confirm` is a hidden alias |
| `--interactive` / `--wizard` | off | open the type-safe **Customize picker** — AskUserQuestion buttons for depth/issues/outputs/scope/cost/hooks (`/deep-init:customize`; see *Customize picker*). `--interactive` canonical; `--wizard` hidden alias |
| `--doctor` | — | preflight report only (tools, scope, config, enabled families); spends 0 tokens |

**Flag interactions:** `--update` and `--decisions-only` are mutually exclusive. `--lint` is read-only (ignores analysis flags, spends 0 tokens — including issue *re-detection*; it only flags *candidate* resolved/critical via citation existence). Mode words (`fast`/`thorough`) set the review path (`thorough` = the adaptive default; `fast` = 0 cycles); there is no cycle-count knob — the cycle-2 quality gate decides whether a 3rd runs. `--horizontal-only` skips component generation. `--heal=apply|auto` never modifies source — only `.ai/` + the canonical lean file's owned-region (`CLAUDE.md` by default) + the dated `.bak` (AC-11). `--issues=off` zeroes the issue-pass cost term and disables `--dashboard`/`--sarif` issue panels (grounded-truth panels still emit).

## Configuration (`.ai/deepinit.config`)
Effective settings resolve in strict precedence (later wins): **built-in max-quality defaults → `.ai/deepinit.config` (project file, optional) → inline flags/mode words**. The config file is plain JSON whose keys are the long-flag names above **without** the leading `--` (e.g. `"depth": "deep"`, `"issues": "on"`, `"issues-families": ["IF-1","IF-2"]`, `"issues-min-severity": "low"`, `"dashboard": "on"`, `"sarif": "on"`, `"heal": "preview"`, `"max-cost": 25, "auto-update": "on"`). Unknown keys are warned-and-ignored (never fatal — R8). It is **read-only input** to a run — a DeepInit *run* never writes it (unlike `.issue_baseline.json`/`.file_hashes.json`, which it owns); commit it to share team defaults. The **one** deliberate exception is the user-invoked `/deep-init:customize` → Freshness step, which may persist just the freshness keys on an explicit confirmation via the surgical schema-validating writer `tools/freshness_config.py` (a *settings* command may write; a *run* may not — see *Freshness controls*). With no config file present, a bare `deep-init` already runs the max-quality defaults — the file exists only to *pin or relax* them per project. The resolved values are echoed in the Wave-0a panel (`--doctor` shows them without spending tokens). **Type-safe editing:** a JSON Schema ships at `skills/deep-init/assets/deepinit.config.schema.json` and DeepInit drops a copy at `.ai/deepinit.config.schema.json` on each run, so adding the `"$schema"` key (below) gives your editor autocomplete + validation for every key, every enum (`depth`/`review`/`heal`/`existing`/`canonical`) and the closed `IF-*` family set — no docs needed, no typos possible. `--doctor` reports whether the file validates.

```jsonc
// .ai/deepinit.config — example (every key optional; omitted keys keep the max-quality default)
{ "$schema": "./deepinit.config.schema.json",
  "depth": "deep", "review": "thorough",
  "issues": "on", "issues-families": ["IF-1","IF-2","IF-3a","IF-4","IF-5","IF-8","IF-3b","IF-7","IF-6","IF-10"],
  "issues-min-severity": "low", "dashboard": "on", "viewer": "on", "sarif": "on",
  "heal": "preview", "max-cost": 25,
  "notify-on-session-start": "on", "notify-on-commit": "on", "auto-update": "off",  // freshness triggers (triggers.md)
  // spec §7 issue controls (issue-filter.md Test-0; gated by §46) — all optional, default = nothing suppressed
  "issues-suppress": [ { "path": "vendor/**", "family": "*" }, { "path": "src/legacy/**", "family": "IF-7c" } ],
  "issues-language-toggles": { "go": { "IF-8": false }, "ruby": { "IF-7c": false } },
  "issues-baseline-accept": [ "IF-3a:src/cache.rb:redis_key" ] }
```

## Customize picker (interactive, opt-in — `/deep-init:customize` or `--interactive`)
The zero-friction default asks nothing. When the user opts in (the `/deep-init:customize` command, the `--interactive`/`--wizard` flag, or a natural-language "let me tweak the settings first"), collect the run settings as **type-safe buttons via the AskUserQuestion tool** — never by making the user hand-type a flag. Ask only these high-value questions; each is Enter-skippable and keeps the max-quality default; every answer maps back to an existing flag / config key (this is a presentation layer — nothing new is introduced):

| # | Question | Buttons | Maps to |
|---|----------|---------|---------|
| 1 | Depth & speed | Deep (default) · Thorough · Fast | `--depth`; **Fast** also sets review=`fast` (0 cycles); Deep/Thorough keep the adaptive review default |
| 2 | Issue detection | All checks (default) · Core checks only · Off | `--issues` + `--issues-families` presets (Core only = IF-1…IF-5) |
| 3 | Outputs *(multi-select)* | Report (Docs+Insights) · Code-scan file | the unified `report.html` + `--sarif` (the code-scan file is the SARIF export) |
| 4 | Scope | Whole repo (default) · Pick parts to analyze | `--components` (picking a list hands off to config/NL) |
| 5 | Spend guard *(pay-per-use)* | $25 (default) · $50 · Custom | `--max-cost` (Custom → a typed value) |
| 6 | Freshness & notifications | Keep defaults · Configure… · Turn the nudge off · Pause in this repo | the freshness config keys + `setup-hooks` (see *Freshness controls* below) |

Keep it to these six — more would regress the zero-friction posture. The full 10-way `issues-families` subset, suppression globs, language toggles, `--canonical`, `--max-lines`, and the rest of the long tail stay in `.ai/deepinit.config` (schema-validated): the picker covers the high-frequency decisions, the config covers everything else. After the picker, echo the one-line resolved panel and proceed (same non-blocking flow as a bare run).

### Freshness controls (question 6 — the one step that PERSISTS)
Questions 1–5 tune the immediate run only. Question 6 is different: it governs the **proactive freshness surfaces** (the plugin-shipped SessionStart staleness nudge + the optional commit breadcrumb / auto-update — `triggers.md`), which are *future* behavior, so its non-default answers are **persisted**, not applied to this run. Present it as type-safe buttons; on **Configure…**, drill into a short follow-up `AskUserQuestion` for the detail (still buttons, never hand-typed):
- **Session-start nudge** — On (default) · Off → `notify-on-session-start`
- **Cadence** — Once per new session (default) · Time window · Every session → `notify-cadence` (+ a window-hours follow-up when *Time window*: 6 (default) · 12 · 24 · Custom → `notify-window-hours`)
- **Commit breadcrumb** — On (default) · Off → `notify-on-commit`; **Auto-update (headless, spends tokens)** — Off (default) · On → `auto-update`
- **Install the commit hook** — Install · Skip → `setup-hooks` (unchanged)

**Persisting the choice — the one narrow config-write exception (R-config).** A DeepInit *run* **never** writes `.ai/deepinit.config` (it stays read-only input — see *Configuration*). This user-invoked Freshness step is the single, deliberate exception: when the user changes a persistent freshness setting, **state exactly which keys will be written and ask for an explicit confirmation first**, then persist via the deterministic, schema-validating writer — never a hand-edit:

```
python "${CLAUDE_PLUGIN_ROOT}/tools/freshness_config.py" --root <repo> --set notify-on-session-start=off --set notify-cadence=window --set notify-window-hours=12 --apply
```

It is **surgical** — it upserts only the named freshness keys and leaves every other key, comment, and the file's layout intact, validating each value against the schema before writing. **Pause in this repo** is the exception's exception: it writes the `.claude/.deepinit-no-nudge` flag (gitignored), not the config. Without an explicit "yes", show the resulting config (run the writer without `--apply` to preview) and let the user save it themselves.

## Translate picker (`/deep-init:translate` or `--translate=<lang>`)
Multi-language reports (`report.<lang>.html`) are a **post-generation overlay** — English `report.html` stays the canonical analysis output (full spec in `references/i18n.md`, C-I18N). When the user runs `/deep-init:translate` **without a language**, open the language picker the same type-safe way as the Customize picker:

1. **AskUserQuestion** — *"Translate the report into which language?"* with the **shipped targets as buttons**: **Spanish (es)** · **Hebrew (he, RTL)**, plus the auto-**"Other"**.
2. If the user picks **Other**, accept **any language** they type — the `other:<language>` escape hatch. Content prose is translated; chrome falls back to English (**stated, never silent**), and the page direction flips for an RTL script. (Shrinking the *shipped/curated* set to Spanish + Hebrew does NOT remove the capability — any language still translates on demand: expand-only.)

Map the answer to a `--translate=<code>` and run the translate stage (`i18n.md`): build/refresh the canonical English report, run the content translation pass into `.ai/i18n/translation_memory.json` (grounded tokens — code, `file:line`, IDs, product nouns — masked + verified, never altered), then emit `report.<lang>.html` (`python tools/build_i18n.py <dir> --lang <code>`; `<html lang dir>`, RTL for Hebrew). The 2 shipped targets are `es he`; any other language works via `other:<language>` (the single source of truth for the shipped set is `tools/build_i18n.py` `LANGS`).

## Run-start prompt — the one consolidated, plain-language pause (R10)
The zero-friction default asks nothing. But three things can genuinely need a decision on a real repo: (a) the repo is large enough that the deepest analysis is a noticeable spend/effort, (b) a database is detected, or (c) a heavy, human-authored front-door file would be rewritten. Rather than three improvised, jargon-leaking pauses scattered across the run — and a front-door question asked twice (the failure that motivated this) — the engine shows **ONE consolidated AskUserQuestion right after detection**, carrying **only the cards that actually apply**, each asked **once**. If none apply, nothing is shown (zero-friction holds).

**This prompt is AUTOMATIC and condition-triggered — it is NOT the opt-in Customize picker and needs no flag.** On a bare `deep-init`, after the silent detect + cost estimate (run-flow step 1), evaluate the three triggers below against the detected facts; if ANY fires, show this prompt. A detected database alone fires the database card; do not conclude "zero-friction, nothing to ask" without first checking the triggers against detection. (The *Customize picker* is the separate, flag-gated tuning surface — `--interactive`/`/deep-init:customize`; it is unrelated to this automatic run-start prompt.) The card set is `tools/prompt_ux.py` `before_i_start_cards()`; every label and body is plain language (**R10** — no internal codes, no mechanics jargon).

| Card (shown only when…) | Plain question | Options *(recommended first)* | Reference logic |
|---|---|---|---|
| **Scope & effort** — the estimate exceeds the `--max-cost` spend guard | *"This is a large codebase — the full deep analysis will take a while and use a noticeable chunk of your Claude usage."* (secondary, de-emphasized: *"≈ $X if you pay per use on API billing; on a Claude subscription this just uses your normal usage."*) | **Full deep analysis** · Faster, lighter pass · Just the main app code · Cancel | `prompt_ux.cost_pause_decision()` → proceed / `--depth=fast` / `--components=` / abort |
| **Database** — a DB is detected | *"I found a database — read it live to check the real schema? (Read-only; I never touch production.)"* + an environment picker (Dev / Staging / Prod) when several configs exist | **No — use the code only** · Yes, read it  *(env picker: the detected configs; a production / managed-cloud host is shown but auto-declined to code-only)* | `db_gate.db_prompt_options()` → static / live (gated by **§R7**) |
| **Existing file** — a heavy, human-authored `CLAUDE.md`/`AGENTS.md`, no resolved strategy | *"You have a large hand-written CLAUDE.md. I can update it (your exact file is saved to a restorable backup), preview my version beside it, or leave it alone and just write the docs."* | **Update my CLAUDE.md** · Preview beside it · Deep docs only | `emit_plan.existing_decision()` → extend / side-file / skip |

**Asked once — never duplicated.** When the existing-file decision is made here, Emit does **not** re-ask it at the end (`generation.md` *the one emit-time confirmation* is the FALLBACK, fired only when this run-start prompt was not shown — e.g. the strategy resolved late). The **recommended option is ALWAYS the stated default** (R10): the scope card → the full deep default; the DB card → the conservative code-only; the existing-file card → `Update my CLAUDE.md` (owns the front door). A saved `.ai/deepinit.config` answer for any card resolves it silently — that card is not shown.

**Render verbatim — this section is the SINGLE source of the user-facing prompt.** Render each card's question and option labels/bodies from THIS section (and its `prompt_ux` / `db_gate` / `emit_plan` reference logic) verbatim. Do **NOT** reconstruct prompt wording from the flag tables above, the `--sarif`/output rows, global-rules §R7's mechanism text, or `detection.md` — those describe the underlying *behavior*, not what the user reads (pulling wording from them is exactly how the old jargon-y prompts crept back in). **Collected up front, asked together:** all needed decisions are asked HERE, once, right after detection — they are NOT deferred to their later pipeline stages and NOT split into separate per-stage prompts. §R7's connection confirmation (run-flow step 5) and the emit-time existing-file confirmation (step 13) **consume** the answer given here; they never render a second prompt.

## Progress presentation — the live "how far along / how much longer" line
A full run is real minutes of work, so between the start panel and the final summary the engine keeps the user oriented with **one terse, plain-language progress line**, refreshed at **each stage boundary** and **each component** as Extract proceeds. It shows two numbers, from two honest sources (the deterministic reference is `tools/progress_model.py`, pinned by harness §98):

- **`% complete` — deterministic, no clock.** A fixed stage-weight model (`progress_model.STAGE_WEIGHTS`: Extract is the largest stage, then Review, then the issue pass), with Extract sub-divided **per component, weighted by lines of code** (`percent_complete()` reads the same `completed{}` map the resume checkpoint already writes — `generation.md`). The active-stage set is frozen at run start (the faster pass drops Review; `--issues=off` drops the issue pass; the weights renormalize), so the bar is **monotonic** — it never goes backwards, and it reaches **100% only when the docs are actually written** (the tail stages are each weighted and each completed, so it walks 95 → 99 → 100, never parks at 90).

- **`time remaining` — an honest forecast RANGE, never a countdown.** The engine (a Claude instance) has **no trustworthy clock** (the timing-honesty ladder, `generation.md`), so time-remaining is a **forecast**: a per-size baseline wall-time × the remaining fraction (`eta_range()`), shown as a **range labelled "estimate"** — e.g. `~6-9 min left (estimate)` — and **omitted entirely** when scope is still unknown (an estimate is a range or an omission, never a single fabricated number — R1). The baseline is the **measured S/M/L corpus** once those metered runs land (`progress_model.TIER_WALLTIME_MIN` ← `STATS.timing`), and a **wider rough band** from the repo's size until then; the range **narrows as the bar advances**, never tightens by a clock the engine cannot trust.

The line is plain language (**R10** — say the OUTCOME, not the internal stage/mechanic; `progress_model.STAGE_VERBS` is scanned by the same banned-term mirror as the run-start prompts, harness §98 G4). Examples — render this shape, never an internal stage code:

```
deep-init: analyzing billing (4 of 7)… 41% — ~6-9 min left (estimate)
deep-init: double-checking the analysis… 78% — ~2-4 min left (estimate)
deep-init: writing docs… 96% — under a minute left
```

This is **informational, never a prompt** — it asks nothing and never blocks the run.

## Run flow — full run
1. **Resolve config + show panel (non-blocking by default).** Silently detect, layer the resolved settings (max-quality defaults ← `.ai/deepinit.config` ← inline flags), and show ONE read-only panel (depth · review mode · components · DB [if detected] · git · existing-front-door handling · enabled issue families · dashboard/SARIF · estimated cost) — then, **whenever nothing needs a decision, proceed automatically, asking nothing**. This is the zero-friction path: the user starts the deepest analysis by typing `deep-init`. When something DOES need a decision (a large repo over the spend guard · a detected database · a heavy human-authored front-door file with no resolved strategy), the run shows **one consolidated, plain-language run-start prompt — only the cards that apply, asked once** (see *Run-start prompt*). Two opt-in escapes: **`--interactive`/`--wizard`** (or **`/deep-init:customize`**) opens the type-safe **Customize picker** — AskUserQuestion buttons, never hand-typed flags — for the high-value choices (see *Customize picker*; each Enter-skippable); a saved `.ai/deepinit.config` is shown as the high-confidence top row and edited in place, never re-interrogated. (A DB live read is always confirmed — global-rules §R7 — and presented plainly via the DB card.)
2. **Detect** (`detection.md`) → `discovery.md` + `structural-graph.json`.
3. **Cost/scale estimate (non-blocking).** Compute the estimate (tokens + $ + scope, **base + issue-pass shown separately** — `detection.md` cost §). Proceed automatically when it is **at or under the `--max-cost` spend guard** (default **$25**); when it is larger, the **scope/effort card** of the run-start prompt (step 1) offers the plain choice — full deep · faster lighter pass · just the main app code · cancel (`tools/prompt_ux.py` `cost_pause_decision()`). The card leads with **scale/effort** and shows the dollar figure only as a secondary line labeled **pay-per-use (API) only** — a Claude subscription is not billed per run. `--no-confirm`/`--yes` suppresses it. (A DB live read is separately gated, global-rules §R7 — never auto-connected.)
4. **Plan** — toposort → Wave 2a (leaves, parallel) / Wave 2b (dependents, dep-ordered).
5. **Extract** (`extraction.md`, + `database.md` if DB in scope) → `.ai/docs/current/components/*.md`.
6. **Horizontal** (`horizontal.md`) → **always emit the six whole-system docs** (default-on; B1) — thin concerns get an explicit "not applicable" stub, never a silent omission.
7. **Review** (`review.md`) — 2 cycles + an adaptive 3rd iff the cycle-2 quality gate still fails (skip in `fast`); report quality score after each.
8. **ADR/KL** (`adr.md`) — extract decisions + the knowledge log (the WHY). Run here as analysis so IF-4 (intent/decision contradictions) has its input.
9. **Issue pass (`--issues=on`, the default).** Consuming the extracted set (BR/IP/WF), the ADR/KL (step 8 → IF-4), live ORM-drift (`database.md` → IF-2), and git change-coupling/hotspot signals (`detection.md` → IF-5): **detect** (`issues.md`) → **raise** (`issue-filter.md` C-RAISE: linter-suppress, root-cause dedup, severity, **polarity-flip SUPPRESSION bias**, and a **FORCED R1.5 back-to-code validate** per semantic issue for IF-1/IF-3a/IF-4 regardless of review mode) → **verify** (`verification.md`, routed by family) → **diff against `.issue_baseline.json`** for lifecycle (new/persisting/accepted/resolved/regressed). Report-only; a false positive is the trust-killer, so when uncertain it omits (AF-1).
10. **Filter** (`filter.md`) → annotate doc findings (lean/deep/drop). Issues are never placed in lean (R9).
11. **Redact** (`redaction.md`) → secret/PII gate over all content **including the issue ledger + dashboard data blob**.
12. **Verify** (`verification.md`) → citation-existence + plausibility over docs; stamp `verified_at`.
13. **Emit** (`generation.md`) → the canonical lean **`CLAUDE.md`** (owned-region, dated `.bak`) + deep `.ai/docs/` (incl. the **issue ledger `issues.md`**) + `manifest.json` (schema 5 — additive: IF-5 metrics + processing timing) + `changelog.md` (incl. issue lifecycle) + `.file_hashes.json` + `.issue_baseline.json` + **`deepinit.sarif`** + self-contained **`dashboard.html`** + self-contained **`docs-viewer.html`** + the **conditional cross-tool `AGENTS.md` export + projections** (when a cross-tool consumer is present / `--emit-agents` / `--canonical=agents`).
14. **Summary** — files written, lean root line count vs budget, coverage %, any `[unverified]`/`[stale]` flags, **issue counts by severity × family + lifecycle deltas + measured-FP note**, next-step hint (`--update` / `--lint` / `--heal` / open the dashboard).

## Run flow — other modes
- `--update` / `--lint` / `--update-adr` → `update.md` (+ `adr.md` for ADR). `--update` also runs the **issue lifecycle diff** (baseline new/persisting/accepted/resolved/regressed); `--lint` stays **zero-token** (candidate resolved/critical only — never re-detects).
- `--heal[=…]` → `heal.md` (governance over `--update`/`--lint`; DEFAULT `preview`, hardcoded report-only floor).
- `--horizontal[-only]` → `horizontal.md`.
- `--decisions-only` → `adr.md`.
- `--doctor` → preflight report (tools, scope, resolved config, enabled families); 0 tokens, no analysis.
- `setup-hooks` → install the commit breadcrumb (`assets/post-commit.sh` into `.git/hooks/`). The proactive **SessionStart** suggestion is **plugin-shipped** (`hooks/hooks.json`) and needs no install — it's active wherever the plugin is enabled (`triggers.md`).

## Prerequisites & degradation
**No tool is a hard prerequisite** — the run never crashes on a missing tool (global-rules §R8). `scc` (sizing) and Graphify (richer cross-file analysis) are *recommended*; absent `scc`, sizing falls back to `find`/`wc` (`detection.md` cost §), and absent Graphify, structure falls back to a grep-based import/symbol graph. Everything else (ctags, gitleaks/trufflehog, LSP, DB tools) is auto-detected at preflight and degrades gracefully.

## Output (what gets written)
```
CLAUDE.md                       # CANONICAL lean root (managed region; content-bearing) — DeepInit owns the front door; never contains issues (R9)
<component>/CLAUDE.md            # lean nested — emitted BY DEFAULT for substantial components (objective rule + the Emit-completeness check in generation.md)
CLAUDE.md.<YYYY-MM-DDThhmm>.bak  # B2 — dated, reversible, redacted backup of a pre-run user-authored context file (pruned to last 1; git history holds the chain)
CLAUDE.deepinit.md              # B3-confirm — only under --existing=side-file ("Preview beside it"): the proposed lean tier next to CLAUDE.md; original left untouched, you merge
.ai/docs/{manifest.json, changelog.md, components/*, decisions.md, domain-model.md,
          technical-dependencies.md, data-layer.md, functional-workflows.md,
          cross-references.md, git-intelligence.md, database-*.md, horizontal/*, archive/,
          issues.md}             # the five horizontal docs always emit (B1); issues.md = the deep-tier issue ledger
.ai/{report.html, dashboard.html, docs-viewer.html, deepinit.sarif}  # CANONICAL unified report (Docs+Insights, ADR-019); dashboard.html + docs-viewer.html are DEPRECATED → emitted as redirect stubs to report.html for one minor version (generation.md), then removed; + SARIF (self-contained, default-on)
.ai/report.<lang>.html  +  .ai/i18n/translation_memory.json   # OPTIONAL translated report (--translate / /deep-init:translate) — post-generation overlay; English report.html stays canonical (i18n.md, C-I18N)
.ai/docs/{.file_hashes.json, .issue_baseline.json}   # state: hashes + the accepted-issue baseline
AGENTS.md  +  .cursor/rules/*.mdc / .github/copilot-instructions.md / .windsurf/rules/*  # CONDITIONAL cross-tool export — only if a cross-tool consumer is present, or --canonical=agents / --emit-agents
```
100% local: read-only analysis, no servers, no data egress. State = flat files + SHA256 hashes. Retrieval = each agent's native loader.
