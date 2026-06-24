# generation.md — C7 Emitter (two-tier output)

Assembles the final output from the annotated findings: a **lean, always-loaded tier** (`AGENTS.md` files) and a **deep, on-demand tier** (`.ai/docs/`), plus manifest, changelog, hashes, and the multi-agent projections. Reads each finding's `tier` (from `filter.md`) and `verified_at` (from `verification.md`). **All content has already passed `redaction.md`.**

This is the largest change from v1: v1 emitted a single comprehensive `AGENTS.md` (≤300 root / ≤200 component). v2 splits into lean + deep, because comprehensive always-loaded context hurts agents (the ETH finding).

## Resume-from-progress (crash / interrupt safety)
A full run is real minutes + tokens (per-component Extract + Review cycles + the horizontal pass). A crash, a closed laptop, or a `--max-cost` stop mid-run must NOT force a restart from zero. DeepInit writes a **per-stage progress checkpoint** `.ai/docs/current/.deepinit_progress.json` as it goes:
```json
{ "run_id": "...", "started": "<iso>", "config": { "depth": "...", "review": "...", "issues": "..." },
  "structural_hash": "<hash of the detected file set + manifest>",
  "completed": { "detect": true, "plan": true,
                 "extract": ["auth", "billing"], "review": ["auth"], "horizontal": false, "emit": false },
  "component_outputs": { "auth": ".ai/docs/components/auth.md", "billing": ".ai/docs/components/billing.md" } }
```
- **Write** after each component's Extract (and each Review cycle) and at every stage boundary — append-only progress, cheap.
- **On (re)start**, if `.deepinit_progress.json` exists AND its `structural_hash` + `config` still match the current run, **offer to resume**: skip the already-`completed` components/stages, reusing their committed `.ai/docs/components/*.md`, and continue from the first incomplete unit. If the structural hash or config changed (code moved, different flags), **ignore the checkpoint** (stale → a clean run; never resume onto a changed tree).
- **Distinct from `--update`** (`update.md`): `--update` is the *incremental-since-last-complete-run* path (DP-1 over a committed baseline); resume is the *finish-an-interrupted-single-run* path. They compose — resume completes the run, then `--update` maintains it.
- **Clear** `.deepinit_progress.json` on a clean completed Emit (it's transient working state, like a `.bak`; never an owned output). Honors R8 (one interruption never corrupts a prior good output — the checkpoint is additive, the real outputs are only finalized at Emit).
- **Drives the live progress bar.** This same `completed{}` map is what the in-run **progress line** computes its deterministic `% complete` from (`tools/progress_model.py` `percent_complete()`; SKILL.md → *Progress presentation*) — so on a resume the bar **continues** from where the interrupted run stopped (e.g. resumes at 40%), never restarting at 0.

## Owned-region writes + the dated reversible backup (default — replaces v1 extend/merge)
DeepInit owns its content via explicit markers; everything outside is human-owned and preserved (CD-3 / D2-013):
```markdown
<!-- DEEPINIT:START (managed — regenerated on each run; edit OUTSIDE these markers) -->
...DeepInit content...
<!-- DEEPINIT:END -->
```
**Before overwriting ANY existing user-authored context file (`CLAUDE.md` / `AGENTS.md` / `.cursorrules`), DeepInit first writes a DATED, REVERSIBLE backup** — `{file}.<YYYY-MM-DDThhmm>.bak` (backlog **B2** — `tools/backup_context.py` is the deterministic reference): the pre-run file, **byte-for-byte REVERSIBLE for a secret-free file** (the common case — the backup IS the exact original), with any embedded secret **masked by the R5 gate** (so a previously-untracked secret is never newly committed into a backup — the ONE deviation from byte-exactness, and it fails SAFE toward over-masking), **committed/visible + root-adjacent** (visibility = trust — a new/untrusting user can SEE the change is reversible, so the `.bak` stays NEXT TO the file it backs up, never tucked into `.ai/` or a hidden dir; the dated `.bak` must NOT be caught by a blanket `*.bak` gitignore — un-ignore the dated form), **pruned to the last N=1 per file** (non-accumulating; the working tree keeps only the most-recent pre-run state — git history holds the full dated chain, so a PILE of dated `.bak`s is clutter the repo doesn't need). This **upgrades** the old transient single `{file}.bak`. Content outside the markers is preserved byte-for-byte. `--existing=skip|extend|replace` overrides (default `extend` = owned-region).

## The canonical lean tier — root `CLAUDE.md` (DeepInit owns the front door)
DeepInit runs as a Claude Code plugin, and Claude Code **auto-loads `CLAUDE.md`** (root AND nested along the path to the file being worked on) but **does not read `AGENTS.md` natively**. So the lean, always-loaded tier's CANONICAL file is **`CLAUDE.md`** — a **self-contained, content-bearing** file (DeepInit is the grounded, verified replacement for `/init`, whose deliverable IS `CLAUDE.md`; `CLAUDE.md` CONTAINS the lean content, **not** a bare `@AGENTS.md` pointer — /init parity, first-impression trust, robustness with no dependency on the `@`-import feature). **DeepInit OWNS this front door:** when it runs, its grounded, verified lean tier **BECOMES `CLAUDE.md`** — this is **product behavior, not a config flag** (there is no "preserve the old file as-is" default); the **dated reversible backup above is the safety mechanism** (R9 honored via REVERSIBILITY + relocation, not in-place freezing — see *Agent-file reconcile* below). ONLY orientation + the highest-value non-obvious facts (filter `tier: lean`).

**HOLD THE LINE ON LEANNESS.** `CLAUDE.md` is the LEAN tier (**~100–150 lines** of the highest-value NON-OBVIOUS facts; budget soft, `--max-lines=root:N` overridable) — architecture, components, key invariants, conventions, gotchas, the WHY. A comprehensive always-loaded file is the exact anti-pattern the product fights (the ETH/LogicStar finding); the comprehensive layer is `.ai/docs/`.

The lean tier renders this template — into **`CLAUDE.md` by default**, or into `AGENTS.md` under `--canonical=agents` / as the cross-tool export below:
```markdown
<!-- DEEPINIT:START -->
# {Project} — Agent Context
{1–2 sentences: what this system is, who it serves}

## Architecture
{style} — {one line}. Components map to `.ai/docs/components/`.

## Components ({n})
- **{name}** — {one-line role}. → `.ai/docs/components/{name}.md`
{…one line each…}

## Critical to know (non-obvious, load-bearing)
{ranked lean-tier findings — contradicts-naive-reading first; then the under-captured behavioral/relational facts (key invariants, boundary/layer rules, the system startup sequence — extraction.md Q10–Q12); then Core BRs, ORM drift, load-bearing workarounds}
- {claim} — `{file:line}`  [{BR-/WF-/WA- id}]

## Where to look
- Component detail → `.ai/docs/components/{name}.md`
- Why decisions were made → `.ai/docs/decisions.md`
- Domain language & ownership → `.ai/docs/domain-model.md`
- End-to-end workflows → `.ai/docs/functional-workflows.md`
- Dependencies & cascade risk → `.ai/docs/technical-dependencies.md`
- Known issues (drift, contradictions, coupling, unenforced rules, risk hotspots) → `.ai/docs/issues.md` {if `--issues`}

## Knowledge Log {if --knowledge-log=on}
{recent high-value KL entries, one line each}
<!-- DEEPINIT:END -->

<!-- HUMAN-AUTHORED — carried forward, never auto-validated or regenerated; edit freely -->
{genuinely-always-needed human directives carried forward from a prior CLAUDE.md — e.g. a git/commit policy, engineering-discipline pointers — preserved VERBATIM here, OUTSIDE the managed markers; the rest of the old human prose is relocated to `.ai/docs/`, and the pre-run original is kept in the dated `.bak` (byte-for-byte for a secret-free file; any secret masked). DeepInit never edits or "validates" this region.}
```

## Existing human-authored front-door file — the one emit-time confirmation (B3-confirm)
On a greenfield repo, or one whose `CLAUDE.md` is already a prior DeepInit owned-region file (`DEEPINIT:START/END` markers present), Emit is **non-blocking** — it proceeds on the default (owns the front door + the dated `.bak`) and merely STATES what it did in the run summary (the zero-friction posture; `SKILL.md` run-flow step 1). But when the repo already carries a **substantial, human-authored** front-door file — a `CLAUDE.md`/`AGENTS.md` with **no `DEEPINIT:START/END` markers** and **> ~200 lines** (the heavy-file flag `detection.md` records) — rewriting it unseen is a first-impression trust risk. So in that ONE case, **and only when the strategy is still unresolved** (no `--existing=…` flag, no `.ai/deepinit.config` `existing` value, and not `--yes`/`--no-confirm`), Emit asks **a single, plain-language confirmation** via the AskUserQuestion tool — the same type-safe button surface as the *Customize picker* (`SKILL.md`), **never a hand-typed flag and never an improvised free-text prompt**. **Asked ONCE.** This confirmation is surfaced preferentially as the *existing-file card* of the consolidated **run-start prompt** (`SKILL.md` *Run-start prompt*) when the run pauses up front; this emit-time confirmation is the **fallback**, fired only when that run-start prompt was not shown (e.g. the strategy resolved after detection) — the front-door question is never asked twice.

The question explains, in plain words: DeepInit replaces the file with a lean, fact-checked tier and relocates the depth into `.ai/docs/`, and the exact original is saved to the dated `.bak` and is restorable. It offers **exactly three REAL options**, each mapping 1:1 to an existing `--existing` strategy — **no invented paths**:

| Button (plain language) | `--existing` | What it does |
|---|---|---|
| **Update my CLAUDE.md** — *recommended* | `extend` | The default: DeepInit updates only its own section of your `CLAUDE.md` and saves your exact current file to a dated, restorable backup. |
| **Preview beside it** | `side-file` | Write DeepInit's proposed version to a separate **`CLAUDE.deepinit.md`** next to your file (Claude Code does NOT auto-load it, so it can never shadow the real one); your `CLAUDE.md` stays **byte-for-byte untouched** for you to merge. Non-destructive. |
| **Deep docs only** | `skip` | Write the deep docs + the report only; leave your front-door files untouched. |

**The recommended option is ALWAYS the stated default** (here `Update my CLAUDE.md` = the `extend` default) — **never** two competing "recommended"/"default" tags on different options, and **never** a recommendation that contradicts the owns-the-front-door positioning. That exact self-contradiction — a fabricated "side-file *(Recommended)*" fighting an "owns CLAUDE.md *(tool default)*" tag, plus an invented `.ai/CLAUDE.deepinit.md` path and leaked jargon ("Lean-tier", "managed region") — is the confabulated-prompt failure **R10** forbids (`global-rules.md`). `side-file` and `skip` are clearly-secondary, conservative fallbacks. After the answer, echo the one-line resolved choice and proceed; the reconcile four-cases below then run unchanged. The reference logic is `tools/emit_plan.py` `existing_decision()` (`§74` pins both).

## Lean nested context file — `<component>/CLAUDE.md` by default (nearest-file-wins — emitted BY DEFAULT for substantial components)
Claude Code reads nested `CLAUDE.md` along the path to the file being worked on, so the nested lean tier is **`<component>/CLAUDE.md`** by default (`<component>/AGENTS.md` only under `--canonical=agents` or in the cross-tool export below). Same managed-region + dated-backup rules; scoped to that component; only its `tier: lean` findings + a pointer to its deep doc. The lean tier is **delivered by default** on a multi-component repo, not skipped. Replace the old vague "substantial enough" judgement with an **objective, default-ON, FILE-AGNOSTIC** rule (it decides WHICH components earn a nested lean file — the canonical basename above decides what it's called; so the engine can't quietly emit only a root file — the B1 under-emit failure):

**Emit a nested lean file BY DEFAULT iff ALL of:**
1. the repo has **≥ 2 components** (on a single-component repo the "nested" file IS the root — don't duplicate); AND
2. the component **owns its own directory** (a path that can host the file — root-loose files have nowhere to put one); AND
3. it is **substantial**: **≥ 2 source files OR ≥ 200 source lines** (a single tiny file is trivial); AND
4. it carries **≥ 1 non-obvious lean finding** (a `tier: lean` BR-/WF-/WA-/IP-/key-invariant/boundary-rule). A substantial component with zero non-obvious facts gets its deep component doc + the root pointer only — a nested lean file would be empty clutter.

**Skips are never silent (R8).** Each component that does NOT get a nested file is **stated in the run summary** with its reason code — `single_component` / `no_own_dir` / `trivial_size` / `no_lean_findings` — exactly like the exclusion-pass accounting; a silent skip reads as "covered" when it wasn't. *(The deterministic reference for this rule is `tools/emit_plan.py`; harness §59 gates it against `mini-multicomponent`. Override the size bar with `--max-lines`/profile flags; `--components=` narrows the set.)*

## Conditional cross-tool `AGENTS.md` export (NOT a default root file)
On a Claude-Code repo a root `AGENTS.md` is **redundant** — Claude Code doesn't read it, and `CLAUDE.md` + `.ai/docs/` already deliver the full two-tier approach — so **a bare run does NOT emit a root `AGENTS.md`** (nor the per-tool projections). DeepInit emits the lean `AGENTS.md` (+ the projections in *Multi-agent projections* below) **only** as a **conditional cross-tool export**, when ANY of: a **cross-tool consumer is detected** (a `.cursor/` dir, `.github/copilot-instructions.md`, a `.windsurf/` dir — `detection.md`'s tool-dir detection) · `--canonical=agents` makes `AGENTS.md` the canonical content file · an explicit `--emit-agents` flag forces it. The cross-tool `AGENTS.md` carries the SAME lean tier and **MUST stay lean** (~100 lines — never a relocated brain). `emit_plan.py` reports `emit_agents_export` + the reason (`not_needed` / `cross_tool_detected` / `canonical_agents` / `forced`); the applied choice is **stated in the run summary** (R8 — never silent). *(`--canonical=claude` is the default; `--canonical=agents` swaps the roles — `AGENTS.md` becomes the content file and `CLAUDE.md` the thin `@AGENTS.md` import. Harness §59 G7 gates this model.)*

## Deep tier — `.ai/docs/` (on-demand, comprehensive, uncapped)
Generation **finalizes** what extraction/horizontal produced in `.ai/docs/current/` into the published `.ai/docs/` layout (no token cap, D2-020):
```
.ai/docs/
  manifest.json
  changelog.md
  components/<component>.md        # the 11 sections (from extraction)
  decisions.md                     # ADR + aggregated Design Rationale (from adr)
  domain-model.md                  # (horizontal 3c)
  technical-dependencies.md        # (horizontal 3a)
  data-layer.md                    # (horizontal 3b)
  functional-workflows.md          # (horizontal 3d)
  cross-references.md              # (horizontal Wave 4)
  shared-state-conflicts.md        # (horizontal 3e — write-conflict correlation matrix)
  git-intelligence.md              # (detection)
  database-schema.md / database-data.md   # (database, if DB analyzed)
  issues.md                        # (C-ISSUE deep issue ledger, if --issues)
  .issue_baseline.json             # (baseline-diff lifecycle; lives beside .file_hashes.json)
  horizontal/<concern>.md          # additional named cross-cutting concerns (--horizontal)
  archive/                         # analyses of removed components (--update)
```
Component deep docs keep the full 11 sections incl. Legacy Warnings + Design Rationale, every `file:line`. `[unverified]`/`[citation-weak]` findings may appear here, clearly marked — never silently dropped.

**`.ai/deepinit.config.schema.json` — the config schema copy.** DeepInit writes a copy of the shipped `assets/deepinit.config.schema.json` into `.ai/` on each run, so a `.ai/deepinit.config` carrying `"$schema": "./deepinit.config.schema.json"` autocompletes + validates offline in the user's editor (enums for `depth`/`review`/`heal`/`existing`/`canonical` and the closed `IF-*` family set). It is **editor convenience, not a runtime gate** — at runtime an unknown/invalid key still warns-not-fails (R8); `--doctor` reports whether the file validates.

**Citation form (emit-side, LESSON 1 / 1b — pairs with `verification.md`).** Every emitted `file:line` is a **full repo-relative path** (`skills/deep-init/SKILL.md:42`, never a bare `SKILL.md:42`): the extraction subagents work inside one component's scope, so the emitter **prefixes each citation with that component's full repo-relative path** before it is written — a bare basename is the easy slip the 2026-06-15 dogfood hit ~1184 times. `verification.md`'s Verify stage normalizes a stray bare basename and flags an ambiguous one (the safety net), but the emitter owns getting it right. And **never cite a `:line` into an inherently-shifting / regenerated file** (`CHANGELOG.md`, `STATS.json`, the regenerated `.ai/docs/` tier) — those line numbers move wholesale on a bump and the cite silently rots; reference such a file at **file level** or pin a stable heading anchor.

## Issue outputs (only when `--issues` is on)
All issue content is **report-only**, **redacted** (runs through `redaction.md` before any disk write), and **never in the lean tier** (R9 / S-3 — the lean root gets only the one-line "Where to look → issues" pointer above).

**`.ai/docs/issues.md` — the deep issue ledger.** A **deep-tier REGENERATED** doc (like the five horizontal docs), with the R3 provenance header — **NOT an owned-region merge** (reserve owned-region + `.bak` for the lean `AGENTS.md` pointer line only). Per-component sections; each row is the `issues.md` §4.1 issue record (`ISS-` id, family, claim, provenance, severity, criticality, priority, certainty, verified, lifecycle, baseline). Only `verified` issues appear as confirmed; `[unverified]`/`[citation-weak]` stay clearly marked. **Dedup spans both representations:** the same drift may be a lean *context fact* (existing v2.0 behaviour, preserved by the Filter) AND an `ISS-` *defect* — the two are deduped, never cross-contaminated (the fact stays lean; the defect is deep-only). **Invariant:** a context fact and an issue are "the same finding" iff they share the issue baseline match-key `(file:line ± symbol)`; when they do, the *fact* may go lean (if non-obvious, per Filter) and the *defect* goes to `issues.md` only — **never the defect in lean, never both copies in lean.** **Worked example:** the fact "`orders.total` is `decimal(12,2)`" is lean context; the IF-2 defect "`orders.total` drifts — model `(10,2)` vs live DB `(12,4)`" shares that `file:line`, so it is emitted to the deep ledger only while the lean tier keeps just the factual type (no defect text, no duplication).

**`deepinit.sarif` — SARIF v2.1.0 (C-SARIF).** `tool.driver.rules[]` = the IF-families (`id: deepinit/IF-x`, `helpUri` → the family doc); each verified issue → `results[]` with `ruleId`, `level` (`error|warning|note` ← severity), `message.text` (the explanation), `locations[].physicalLocation` (`artifactLocation.uri` + `region.startLine` ← `file:line`), and `partialFingerprints` (← the **baseline match key**, via the shared normalization primitive defined in `issues.md` — enabling consumer-side baselining). **Semantic families (IF-1/IF-3a/IF-4) default to `note`/`warning`, never `error`,** until DeepInit's OWN measured FP justifies it (never a borrowed vendor severity; never flood a code host's Security tab). Emitted **downstream of redaction**; plugs into the existing D2-014 multi-agent-projection slot.

Emit exactly this shape (the **machine-readable** contract GitHub code scanning ingests — the prose above maps onto these fields; the mandatory keys are `$schema`, `version: "2.1.0"`, `runs[].tool.driver.name`, and per-result `ruleId`/`level`/`message`/`locations`/`partialFingerprints`). `tool.driver.version` MUST be the **loaded DeepInit version** the run reports — never a fixed string; the `version` value in the example below is illustrative):
```json
{
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "DeepInit",
          "informationUri": "https://github.com/deepfusionlabs/deep-init",
          "version": "0.39.0",
          "rules": [
            {
              "id": "deepinit/IF-2",
              "name": "DbCodeDrift",
              "shortDescription": { "text": "DB-vs-code drift (ORM disagrees with the live schema)" },
              "helpUri": "https://github.com/deepfusionlabs/deep-init/blob/main/skills/deep-init/references/issues.md"
            }
          ]
        }
      },
      "results": [
        {
          "ruleId": "deepinit/IF-2",
          "level": "warning",
          "message": { "text": "Possible model-only field: the ORM validates external_billing_id presence, but no such column appears in the live subscriptions schema." },
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": { "uri": "app/models/subscription.rb" },
                "region": { "startLine": 23 }
              }
            }
          ],
          "partialFingerprints": { "deepinitBaselineKey/v1": "IF-2:app/models/subscription.rb:Subscription#external_billing_id" }
        }
      ]
    }
  ]
}
```
`runs[].results[]` is empty (`[]`) when no issues survive verification — still a valid run. `ruleId` MUST match a declared `tool.driver.rules[].id`. `partialFingerprints` is the **only** result-level key DeepInit uses for stable baselining — its value is the `issues.md` match key serialized as `{family}:{relative_path}:{enclosing_symbol}#{disambiguator}` (line numbers deliberately excluded, so a line shift does not churn the fingerprint). The `#`-suffix is the **intra-symbol disambiguator** — the member/field name where structurally available (e.g. `Subscription#external_billing_id`), else the per-symbol ordinal of issues.md:54 (e.g. `Subscription#0`).

**`.ai/dashboard.html` — the dashboard (C-DASH). [DEPRECATED → superseded by `.ai/report.html` (C-REPORT, ADR-019).]** A single self-contained vanilla-JS / inline-CSS artifact (no framework, no CDN, no network) that reads an embedded JSON blob from the ledger + manifest. Full panel spec in `dashboard.md`. Generated (R3 provenance), **regenerated not hand-edited** — unlike `AGENTS.md` it has no owned-region protection; **redaction runs over the embedded JSON before embed.** **Deprecation (one-minor-version window):** the unified report is now the canonical human artifact; for the window the skill emits this path as a tiny **redirect stub** (`skills/deep-init/assets/legacy-stub-template.html` → `report.html`) so old bookmarks still resolve, then removes it in a later release. The full template still ships meanwhile (expand-only; harness §16 still gates it). The `--dashboard` flag is preserved for anyone who wants the full standalone artifact.

**`.ai/docs-viewer.html` — the docs-navigation viewer (C-VIEW). [DEPRECATED → superseded by `.ai/report.html` (C-REPORT, ADR-019).]** A single self-contained vanilla-JS / inline-CSS **READER** over the *generated documentation* — the lean `AGENTS.md` + the component-doc tree + the ADR/KL decisions narrative + the issue ledger — with search, a component tree, jump-to-`file:line`, an architecture overview, a decisions timeline, and cross-reference linking. The docs are for the coding agent to consume; this is the **human-facing first impression**. Built by `tools/build_docs_viewer.py` from `skills/deep-init/assets/docs-viewer-template.html`; the corpus is embedded as one escaped inline JSON island (`<`/`>` escaped so an analyzed-repo `</script>` can't break the page) and rendered safely (createElement + textContent, element + URL-scheme allow-lists — no `innerHTML`/`eval`). A **docs reader, NOT a graph explorer** (DeepMap, S-8); a **separate artifact** from the issue dashboard. Generated (R3 provenance), regenerated not hand-edited; **redaction runs over the corpus before embed.** Full spec in `viewer.md`; default-on is gated on zero off-host refs (harness §43). **Deprecation (one-minor-version window):** same as C-DASH — superseded by the unified report; emitted as a redirect stub (`legacy-stub-template.html` → `report.html`) during the window (full template still ships; §43 still gates it), removed in a later release. The `--viewer` flag is preserved.

**`.ai/report.html` — the unified Docs + Insights report (C-REPORT) — the canonical human artifact.** The self-contained, co-branded artifact ("DeepInit, by Deep Fusion Labs") that **MERGES** the docs reader (**Docs** view) + the issue/metrics dashboard (**Insights** view) into one file with a top-level view switch + a ⌘K command palette; built deterministically by `tools/build_report.py` (reuses the `build_docs_viewer` parsers) from `skills/deep-init/assets/report-template.html`. Vendored libraries (markdown-it / DOMPurify / highlight.js) are **inlined at build time, never CDN** — the constraint is no view-time network, NOT zero-dependency. **Supersedes C-VIEW + C-DASH**, which are now DEPRECATED: for one minor version their paths emit a redirect stub to `report.html` (`skills/deep-init/assets/legacy-stub-template.html`), then they are removed (the full templates + §16/§43 stay until then — expand-only). Full spec in `report.md` (ADR-019); verified by `tools/smoke_report.mjs`.

**`.ai/docs-viewer.html` / `.ai/dashboard.html` redirect stub (deprecation window).** `skills/deep-init/assets/legacy-stub-template.html` — a tiny self-contained page (strict CSP `default-src 'none'`, 0 off-host refs, no JS sink) with a `<meta http-equiv="refresh">` + a visible **relative** `report.html` link. Emitted verbatim at both legacy paths during the deprecation window so old links/bookmarks land on the unified report; removed once the window closes. (Harness §70 gates the stub's self-containment + the deprecation being stated, not silent.)

**`.ai/report.<lang>.html` — translated report (C-I18N, optional).** When `--translate=<lang>` is set (or `/deep-init:translate` is run), DeepInit emits a per-language copy of the report as a **post-generation overlay** — English `report.html` stays the canonical analysis output and is never altered. The skill runs the content translation pass over the report's PROSE fields into `.ai/i18n/translation_memory.json` (grounded tokens — code, `file:line`, IDs, product nouns — masked + verified, never altered), then `tools/build_i18n.py <dir> --lang <code>` emits `report.<lang>.html` (deterministic; `<html lang dir>`, RTL for Hebrew; chrome from the template's baked `STRINGS`). Shipped: `es he` (+ `other:<language>`). Misses honest-degrade to English (never blank). Full spec in `i18n.md`; gated by harness §71.

## `manifest.json` (schema_version 3 → 5 — additive: FL-5/IF-5 metrics + processing timing)
Old fields preserved; old consumers tolerate unknown fields (expand→migrate→contract). A `schema_version: 2`/`3` manifest is still tolerated, and a **missing `issues` index is treated as an empty baseline** so the first incremental run on a pre-issue-layer repo never errors. **Schema 4 adds an additive `components.<name>.metrics` block** (IF-5 risk signals — below); a schema-3 manifest with no `metrics` is read as the honest **"metrics unavailable"** state (`report.md` Insights / harness §67 G5), never fabricated zeros.

**Schema 5 adds an additive top-level `processing_metrics` block** — the per-stage timing the user sees ("where did my run's time go"). The Emit stage writes `processing_metrics: {schema_version: 5, stages: [{name, duration_sec, tokens_in, tokens_out}], per_component: [...], throughput: {loc_per_sec, components_per_min, tokens_per_loc}, parallelism: {wave_2a_speedup, ...}}` from the stage-timing stamps the run recorded (extraction.md → "Stage-timing emission"). A schema-4 manifest with no `processing_metrics` is read as the honest "timing unavailable" state — never fabricated. **Timing-source honesty ladder** (the timing analogue of `token_source`): **`external_metered`** (a metered runner bracketed the stages — the ONLY grade a *published* wall-clock figure may use) › **`engine_stage_stamps`** (the engine self-reported the stamps — reliable for *attributing* time per stage, NOT for the publishable total; a Claude instance has no trustworthy monotonic clock) › **`formula_estimate`** (apportioned from the token split). The canonical timing schema + the recompute-honesty rule live in `docs/reference/deepinit-instrumentation-schema.md` → `cost.processing{}`; a metered validation run folds the same data into the committed cost ledger.
```json
{
  "schema_version": 4,
  "deepinit_version": "2.0.0",
  "run_id": "{RUN_ID}",
  "generated": "{ISO}",
  "components": {
    "auth": {
      "doc": ".ai/docs/components/auth.md",
      "files": ["..."],
      "content_hash": "sha256:…",
      "interface_hash": "sha256:…",
      "verified_at": "{ISO}",
      "metrics": { "risk": 3062.0, "churn": 12, "bus_factor": 1, "coverage": null, "criticality": "Core" }
    }
  },
  "deep_docs": ["decisions.md","domain-model.md","technical-dependencies.md","data-layer.md","functional-workflows.md","cross-references.md"],
  "issues": { "ledger": ".ai/docs/issues.md", "sarif": ".ai/deepinit.sarif", "baseline": ".ai/docs/.issue_baseline.json", "counts": {"open": 0, "resolved": 0, "regressed": 0, "by_severity": {}} },
  "dashboard": ".ai/dashboard.html",
  "lean_budget": {"root": 100}
}
```
**`components.<name>.metrics` (schema 4 — the IF-5 risk producer).** The skill writes this block **the moment it computes IF-5** (`issues.md` §IF-5), so the report's Insights risk heatmap shows real ranked data:
- `risk` — the IF-5 priority score `1000*CRIT + churn_6mo + (100 - coverage_pct) + (50 if bus_factor==1 else 0)`, `CRIT = {Core:3, Supporting:2, Peripheral:1}`. **One source of truth = the formula at `issues.md` §IF-5**; the deterministic reference-impl is `tools/risk_metrics.py` (harness §19 pins the two in lockstep). The dominant `1000*CRIT` term keeps criticality above raw churn (not-churn-only).
- `churn` — commits touching the component in the 6-month window (git-intel, `detection.md`).
- `bus_factor` — author bus-factor (git-intel); the `+50` term applies only when it is `1`.
- `coverage` — test coverage %, or **`null`** when no coverage signal exists (the `(100 - coverage_pct)` term is then dropped — **honest-degrade, never a fabricated 0/100**, R1).
- `criticality` — `Core` / `Supporting` / `Peripheral` (from `extraction.md`).

**Honest-degrade (R1).** On thin git history (shallow/young repo — `detection.md` history-depth preflight tags IF-5 `[LOW]`) the skill MAY omit `metrics` entirely rather than publish a low-confidence hotspot; `build_dashboard` then renders the "metrics unavailable" state (§67 G5). Never a confidently-wrong zero (KL-learning:001).

## `.file_hashes.json` (drives `--update`)
Per file/component: `content_hash` (SHA256 of source) + `interface_hash` (SHA256 of the canonicalized **public surface**). Written every run; read by `update.md`.

**Public-surface extraction (language-agnostic — pin it, don't improvise; the DP-1 skip AND the issue baseline match-key both rest on it).** The public surface is the **sorted, canonicalized list of exported symbol signatures** — name + param arity/kind + visibility, **excluding bodies, comments, and line numbers** — so a body-only edit leaves `interface_hash` unchanged while an export add/remove/signature change moves it.
- **Primary (Graphify present):** each component's `exports` from `structural-graph.json`.
- **Fallback (Graphify absent):** grep the public-declaration patterns per language, capturing the **signature line, not the body**:
  - **TS/JS** — `export (async )?(function|const|class|interface|type|enum) NAME` · `export { … }` (incl. `as` aliases) · `export default` · **re-export forms** `export * [as NS] from` / `export { … } from` · `export =` · **CommonJS** `module.exports[.X] =` / `exports.X =`
  - **Python** — module-level `def NAME(` / `class NAME` where NAME has no leading `_` (PEP-8 public), or names in `__all__` (a **dynamic / mutated `__all__`** — `+=`, comprehension — is an unresolved indicator → fold, below)
  - **Ruby** — `def NAME` / `class NAME` / `module NAME` above any `private` keyword (public methods only)
  - **Go** — Capitalized top-level `func`/`type`/`const`/`var` (exported)
  - **Java/C#** — `public`/`protected` member + type signatures
  - **Rust** — `pub fn`/`struct`/`enum`/`trait`/`mod`
- **Canonicalize identically across both layers** (sort; collapse whitespace; keep names + arity; drop bodies) so the hash is layer-independent.
- **Completeness reconciliation (grep path) — the precision guard against a MISSED propagation.** A *partial* extraction is more dangerous than a total failure: if the grep captures *some* exports but silently drops a form outside its patterns, `interface_hash` looks valid yet won't move when that dropped export later changes — a dependent is then **wrongly skipped (stale docs, not just wasted tokens)**. So reconcile the captured signatures against export-**indicator** tokens — any token that can introduce a public name (the re-export / `as`-aliased / CommonJS / dynamic-`__all__` forms above), counting brace-list and `__all__` members **member-by-member**. If **any indicator is unresolved** (a form the patterns can't fully capture, or whose re-export target is `[SKIPPED]`) the surface is **INCOMPLETE** → apply the degrade-safe fold below. **Zero indicators** → a confidently-empty surface (no fold; precision preserved). This **subsumes** total-failure (the all-unresolved special case). *(Harness §63 is the deterministic instance — a naive grep misses an `export *` / aliased re-export change; the completeness rule folds and propagates.)*
- **Degrade safe:** if a file's public surface can't be extracted at any layer (parse failure / exotic language) **or the reconciliation above marks it INCOMPLETE**, do NOT skip its dependents — fold the file's `content_hash` into the interface so DP-1 conservatively re-analyzes dependents (wasted tokens, never a missed propagation). Log it (R8). *(The harness DP-1 test §7 is the TS instance of this; §19 exercises the Python fallback; §63 the completeness fold.)*
- **Resolve-to-literal sibling pass (value-carrying; used ONLY by IF-10 cross-module §29 — expand-only, never folded into `interface_hash`/IF-3b/IF-8, which stay value-free name-set membership).** The public surface above is deliberately **value-free** (name + arity + visibility, no RHS). The IF-10 cross-module slice needs ONE extra fact the canonical surface omits: the **literal RHS of an `export const NAME=<literal>`**. So a *separate* pass records, per component: (1) a **literal-export table** `export const NAME=<LIT10>` → (component, file:line, literal); (2) **re-export edges** `export { NAME [as A] } from './rel'` and `export * from './rel'`; (3) the **named-import table** `import { NAME [as L] } from './rel'` (namespace/dynamic/type-only/default imports are NOT recorded → excluded by form). Resolving an imported NAME walks the re-export chain (`posixpath.normpath` to the target component, bounded depth, cycle-guarded) to its unique literal origin; **≥2 distinct origins → suppress (ambiguous), 0 → suppress (dead-end/non-literal/`export let`)**. This pass can ONLY *suppress* or carry a **grounded** origin `file:line` — it never name-keys (the honesty bar §29 GATE-10 enforces). It is **read-only and additive** — it does not alter the canonical public surface, the interface hash, or any other family. *(Harness §29 is the deterministic instance; the off-TS form — Python `FLAG=False; from a import FLAG; if FLAG:` — is the same one-hop fold, the moat, not separately gated.)*
```json
{
  "version": 1,
  "generated": "{ISO}",
  "run_id": "{RUN_ID}",
  "components": {
    "auth": {
      "content_hash": "sha256:…",
      "interface_hash": "sha256:…",
      "files": ["src/auth/login.ts", "src/auth/register.ts"],
      "last_analyzed": "{ISO}"
    }
  }
}
```

## `changelog.md`
Append-only, typed:
```markdown
## {ISO} — Run {RUN_ID}
### ADDED
- {component/finding}
### MODIFIED
- {component} — {what changed}
### BREAKING
- {interface change} — affects {dependents}
### ISSUES (lifecycle — a PARALLEL section, never mixed into BREAKING/MODIFIED)
- NEW: {ISS-id} {family} — {claim} `{file:line}`
- RESOLVED: {ISS-id} — no longer detected + re-verified gone
- REGRESSED: {ISS-id} — reappeared after being resolved
```

## Knowledge Log
If `--knowledge-log=on` (default): emit `KL-{category}:{nnn}` entries (8 categories) — high-value ones to the lean root, full set to the deep tier / `decisions.md` neighborhood.

## Indexability (so agents can navigate)
Consistent header hierarchy; stable anchors; IDs in headers where referenced; every cross-doc reference is a relative link; a "Where to look" index in the lean root. Tables for scannable data (BR/IP/drift); prose for rationale.

## Emit-completeness check (pre-finalize — the forcing function for B1)
Before declaring done, verify the promised two-tier set actually exists on disk — a forcing function so the run can't quietly under-emit one root file (the B1 failure). Compute the expected manifest with the rule above (`tools/emit_plan.py` is the reference, `root_lean_file` = the canonical basename) and confirm:
- the lean **root canonical file** (`CLAUDE.md` by default; `AGENTS.md` under `--canonical=agents`) was written (owned-region + the dated `.bak`); AND
- under `--canonical=agents`, the **thin `CLAUDE.md` `@AGENTS.md` import** (`import_stub_file`) was ALSO written — it is the SOLE Claude-Code auto-load surface in that mode (Claude Code can't read `AGENTS.md` natively), so skipping it auto-loads NOTHING (a B1-class silent under-emit); under the default (`canonical=claude`) there is no separate stub (`CLAUDE.md` IS the content); AND
- a nested **`<component>/<canonical>`** lean file exists for every component the rule marks for emission (and ONLY those — every other component is stated-as-skipped, never silent); AND
- the **six whole-system horizontal docs** (`technical-dependencies.md`, `data-layer.md`, `domain-model.md`, `functional-workflows.md`, `cross-references.md`, `shared-state-conflicts.md`) all exist — each substantive OR an explicit "not applicable — <reason>" stub, **never silently missing** (`horizontal.md` mandates this; folds into the root only on a Tiny single-component target, and says so); AND
- the **cross-tool `AGENTS.md` export** was emitted IFF `emit_agents_export` is true (a cross-tool consumer detected, `--canonical=agents`, or `--emit-agents`) — NOT a redundant root `AGENTS.md` on a Claude-Code-native run; AND **each per-tool projection** (`.cursor` / `.github` / `.windsurf`) was emitted IFF ITS OWN tool-dir/`--emit-*` condition holds (the `cross_tool_consumers` list, never the full projection set merely because `emit_agents_export` is true — per-tool detect-or-flag, *Multi-agent projections* below).

Any gap → emit the missing file (or, for a deliberate fold, record the explicit reason). The completeness summary (what was emitted, what was skipped + why, the canonical choice + agents-export reason) is **stated in the run summary** — R8 honesty, never a silent omission. *(Harness §59 pins this contract.)*

## ID-consistency check (pre-finalize)
Verify: no duplicate IDs within a scope; every referenced ID exists; `BR/WF/IP` numbering contiguous per scope; cross-doc ID references resolve. Failures → fix before finalizing (and surfaced by `--lint` later).

## Agent-file gitignore policy (B4 — mirror the SHARED file, transparently)
deep-init writes the canonical `CLAUDE.md` + (conditionally) the cross-tool `AGENTS.md` export + projections (`.cursorrules` / `.github/copilot-instructions.md` / `.windsurf/rules/*`). Their gitignore state should match the project's INTENT, governed by **`--gitignore-agents=auto|on|off`** (default **`auto`**):
- **`auto`** — **mirror the SHARED agent file's gitignore state.** Detect whether the project gitignores its shared agent file (`CLAUDE.md` / `AGENTS.md` — checked via `git check-ignore`); if it does, **mirror** that intent onto the generated `AGENTS.md` + projections (gitignore them too); otherwise leave them committed/visible. **`CLAUDE.local.md` is explicitly NOT the shared file** — it is *meant* to be local (a personal override), so its being ignored never implies the shared agent files should be.
- **`on`** — always gitignore the generated agent files. **`off`** — always leave them committed/visible.
- **Always STATE the applied policy in the run summary** (which files, ignored-or-committed, and why) — **never silently**. And **never silently auto-edit `.gitignore`**: adding an ignore entry is a tracked-file write, so deep-init surfaces the exact line it would add and applies it transparently (or leaves it to the operator), honoring draft-only git discipline.
- **Boundary:** **redaction (R5) stays the secret guard** — gitignore is **intent-respect + defense-in-depth, NOT a secret mechanism** (a gitignored file still sits in the working tree, one `git add -f` from a commit). Secrets are stripped by `redaction.md` before any write regardless of gitignore state. For a repo whose `CLAUDE.md` is committed (the common case), the generated agent files default to committed/visible (visibility = trust).

## Multi-agent projections (D2-014)
- **Claude Code / Antigravity** — consume the skill package (`SKILL.md` + `references/`) for on-demand depth; `.ai/docs/` is the shared substrate.
- **Codex / generic (AGENTS.md consumers)** — the lean `AGENTS.md` (root + nested, nearest-file-wins) is the native loader; emitted as the **conditional cross-tool export** (above), not by default on a Claude-Code-native run.
- **Cursor** — project `.cursor/rules/*.mdc`: **one `.mdc` per `.ai/docs/components/<component>.md`** with `globs:` set to that component's paths (`agent-requested`/auto-attach on matching files), plus a single **`alwaysApply: true`** rule carrying the lean-root highlights. Each `.mdc` front-matter: `{description, globs, alwaysApply}`; body links to the deep doc. Emitted when a `.cursor/` dir exists or `--emit-cursor` is passed.
- **CLAUDE.md — the CANONICAL content-bearing lean tier + agent-file RECONCILE (B3, revised).** `CLAUDE.md` is NOT a projection — it is the **canonical, content-bearing** lean artifact DeepInit OWNS (see *The canonical lean tier* above); Claude Code auto-loads it but **does not read `AGENTS.md` natively** (verified vs the official docs — 5+ open feature requests). When deep-init meets existing agent files it **reconciles** them into ONE canonical lean artifact, never orphans a second divergent copy; the EXACT prior file is kept in the dated `.bak`, and genuinely-always-needed human directives are carried forward into the human-owned region (above). **Reconcile the four cases** (detected in `detection.md`):
  - **only-CLAUDE.md** → the grounded lean tier **BECOMES `CLAUDE.md`** (owns the front door); the prior file is archived to the dated `.bak`, its always-needed human directives carried forward, the rest of its prose relocated to `.ai/docs/`. **Never an in-place freeze of a stale, unvalidated body** (the safety is reversibility, not preservation-as-primary).
  - **only-AGENTS.md** → reconcile to `CLAUDE.md` as the canonical Claude-Code-native tier; keep the lean `AGENTS.md` as the cross-tool export (same lean tier, deduped).
  - **both** → `CLAUDE.md` is canonical; keep `AGENTS.md` as the lean cross-tool export (deduped — one lean tier, two surfaces).
  - **neither** → emit `CLAUDE.md` (Claude-Code-native); add the `AGENTS.md` cross-tool export only if a cross-tool consumer is present (the conditional rule above).
  In EVERY case the lean tier **MUST stay lean** (~100–150 lines, highest-value non-obvious facts only; depth → `.ai/docs/`) — **never** relocate a brain into it (the core two-tier thesis). Honors **owned-region + the dated `.bak` + byte-preservation** (R9 via reversibility). *(Advanced, OFF by default: **`--canonical=agents`** swaps the roles — `AGENTS.md` becomes the content file and `CLAUDE.md` a thin **`@AGENTS.md` import** (Claude Code's `@path`, expanded at launch, no duplication); the niche AGENTS-first path.)*
- **GitHub Copilot** — `.github/copilot-instructions.md` (Copilot's repo-wide custom-instructions file): the lean-root highlights rendered as plain Markdown guidance (no front-matter; Copilot reads the whole file). **Owned-region** wrapped + `.bak` + redaction, same discipline. Emitted when a `.github/` dir exists or `--emit-copilot` is passed.
- **Windsurf** — `.windsurf/rules/*.md` (Windsurf reads a directory of rule files; legacy single `.windsurfrules` also supported): **one rule file per component** (mirroring the Cursor mapping — component paths in the rule's activation glob) + an always-on lean-highlights rule. Owned-region + `.bak` + redaction. Emitted when a `.windsurf/` dir (or `.windsurfrules`) exists or `--emit-windsurf` is passed.

**All projections are deterministic transforms of the ALREADY-redacted, already-verified lean tier** — they add no new findings, never the deep `issues.md` defects (R9: issues never enter a lean/always-loaded surface), and each file-writing projection honors the owned-region + `.bak` + byte-preservation invariant. Detect-or-flag: a projection emits only when its tool's directory is present OR its `--emit-*` flag is passed (never litter a repo with config for tools it doesn't use).

## Pre-finalize quality gate
Run the three-facet check (`review.md`: Completeness / Helpfulness / Truthfulness, ≥3 each on the deep docs) before declaring done; below threshold → recommend another review cycle (unless `fast`).
