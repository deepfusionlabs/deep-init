# Global Rules — apply to ALL stages and subagents

These rules bind every stage of the pipeline (Detect → Plan → Extract → Filter → Redact → Verify → Emit) and every subagent. Each component reference file assumes these.

## R1 — Never fabricate
Every finding MUST cite a source `file:line`. Certainty levels:
- `[HIGH]` — directly observed in code, `file:line` available.
- `[MEDIUM]` — inferred from patterns (naming/structure implies it, no explicit doc).
- `[LOW]` — speculative, limited evidence.

Prefer omission over speculation. If uncertain, mark `[LOW]` or move to Open Questions. A confidently wrong claim is worse than a gap.

**Exact counts, enumerations, AND absolute quantifiers are HIGH-confidence claims too.** A specific number or closed "the N items" set — "22 test files", "4 overloads", "9 ADRs", "the three handlers" — and an absolute quantifier — "**every** / **all** / **always** / **never** / **only** / **mandatory**" — is a factual assertion that MUST be checked against the code before it is stated: actually count it, and for a universal confirm there is **no counterexample** (one missing case refutes an "every"/"all" claim). Otherwise soften to an unbounded/qualified form ("several test files", "most modules", "typically") or drop it. An unverified count or universal asserted as fact is an R1 violation **even when the surrounding prose is correct**. (Measured: a DeepInit-vs-`/init` benchmark found off-by-one counts were the dominant wrong-HIGH failure mode; after a fix corrected them, a re-run surfaced false universals as the next class — e.g. "`from __future__ import annotations` in EVERY module" when one file lacked it. See `validation/matrix/m1b_init_head_to_head.json`.)

## R2 — Strict input boundaries
Each subagent reads ONLY its designated inputs:
- Component-extraction subagents: ONLY files within their component path.
- DB subagents: ONLY database queries + config files.
- Horizontal subagents: ONLY `.ai/docs/` outputs from prior stages (plus targeted code reads).
- Review-investigation subagents: ONLY files relevant to the specific issue.

No subagent crosses into another's territory. If it needs out-of-scope information, it notes the gap and moves on.

## R3 — Provenance metadata
Every output file begins with:
```markdown
<!-- DeepInit {stage} | Component: {name or "system-wide"}
Run ID: {RUN_ID}
Input files processed: {list}
Generated: {ISO date} -->
```

## R4 — Mandatory sections
All sections defined in a template MUST appear, even if empty. Empty sections carry a one-line explanation (e.g. "No integration points — all data access is internal"). This lets a reader distinguish "not found" from "not checked."

## R5 — Sequential ID system
IDs are scoped to prevent collisions:

| Type | Format | Scope | Example |
|------|--------|-------|---------|
| Business Rule | `BR-{comp}:{nnn}` | per component | `BR-auth:001` |
| Domain Rule | `DR-{nnn}` | system-wide | `DR-001` |
| Workflow (component) | `WF-{comp}:{nnn}` | per component | `WF-auth:001` |
| Workflow (cross-component) | `WF-{nnn}` | system-wide | `WF-001` |
| Integration Point | `IP-{comp}:{nnn}` | per component | `IP-auth:001` |
| User Story | `US-{nnn}` | system-wide | `US-001` |
| Use Case | `UC-{nnn}` | system-wide | `UC-001` |
| Critique Finding | `CR-{nnn}` | per review cycle | `CR-001` |
| Workaround | `WA-{nnn}` | system-wide | `WA-001` |
| Architecture Decision | `ADR-{nnn}` | system-wide | `ADR-001` |
| Knowledge Log | `KL-{category}:{nnn}` | per category | `KL-learning:001` |
| Issue (component) | `ISS-{comp}:{nnn}` | per component | `ISS-auth:001` |
| Issue (system-wide) | `ISS-{nnn}` | system-wide | `ISS-001` |

Numbering starts at 001 per scope. Valid KL categories: `progress`, `learning`, `architecture`, `solution`, `mistake`, `integration`, `debug`, `preference`.

## R6 — Layered detection (principle)
Extract structural information deterministically before spending LLM tokens — cheaper and more truthful. Layers are ADDITIVE; later layers enrich, they don't replace. If a layer is unavailable, skip and continue. Tag every file with extraction confidence: `[GRAPHIFY]` > `[CTAGS]` > `[GREP]` > `[LLM-ONLY]`. **Full ladder + import patterns: see `detection.md`.**

## R7 — DB security (hard gate)
Before connecting to ANY database:
1. Show the detected connection string to the user (mask the password).
2. Require explicit confirmation BEFORE connecting — but the user-facing ASK is the **plain database card** of the Run-start prompt (*"I found a database — read it live to check the real schema?"* · Yes / No — use the code only; `SKILL.md` *Run-start prompt*, `database.md`), NEVER a raw "Connect to {host}:{port}? (y/n)" string or any internal term. The masked connection string is supporting detail under the card; the y/n decision the card returns IS this confirmation (the engine does not re-ask it as a separate prompt).
3. REFUSE if the connection string contains `prod`, `production`, `master`, or a known production cloud host (e.g. a managed-DB endpoint such as `*.rds.amazonaws.com`, `*.database.azure.com`, `*.cloudsql.*`, or any host the user confirms is production — non-exhaustive; refuse on any production signal).
4. ALL queries are READ-ONLY: `SELECT` and `information_schema` only. No `INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE` under any circumstance.
5. Prefer an installed MCP DB tool over a raw CLI.

Detection priority: MCP tool → CLI tool → neither (skip DB analysis, note it). This gate is mandatory and applies wherever a DB is touched (see `database.md`).

**The user-facing FACE of this gate is plain (R10).** When a DB is detected, the run offers a live read in plain words — *"I found a database — read it live to check the real schema? (Read-only; I never touch production.)"* — with an environment picker (Dev / Staging / Prod) when several configs exist, and NEVER the internal vocabulary the improvised prompt leaked ("Database analysis for ORM-drift (IF-2)?", "live-drift", "information_schema", "EF migrations", "NPoco"). The conservative recommendation is code-only (don't connect). The deterministic option logic is `tools/db_gate.py` `db_prompt_options()`, which reuses `classify_host` so a production / managed-cloud host is **auto-declined to code-only** (shown, never offered as a live target); the prose card is in `database.md`. The y/n confirmation, the production-refusal, and the read-only restriction above are UNCHANGED — only the presentation is plain.

## R8 — Per-file graceful degradation
A failure in one file MUST NOT block the pipeline. Per source file: attempt highest available layer (Graphify AST) → fall back to grep → fall back to `cat` + LLM-only → if all fail, skip and log the reason. Tag each file `[GRAPHIFY]` / `[CTAGS]` / `[GREP]` / `[LLM-ONLY]` / `[SKIPPED:{reason}]` (the five fallback outcomes — reconciles with the R6 / detection.md confidence ladder). Never abort a stage because one file failed; list skipped files in a "Skipped Files" subsection.

## R9 — Non-obviousness governs placement (v2)
Every finding carries a `non_obvious` verdict (+ reason) from the Filter stage (see `filter.md`). The verdict decides **placement, never deletion**:
- The **lean, always-loaded tier** (`AGENTS.md`) gets ONLY the highest-value non-obvious facts.
- The **deep, on-demand tier** (`.ai/docs/`) gets **everything** — comprehensive, uncapped.
- Trivially-inferable noise (derivable from signatures/types/names/standard conventions) is dropped from the lean tier only; kept in deep if still useful.

When in doubt, keep in deep. A filter miss must mis-place a fact, never lose it. Leanness applies only to the always-loaded slice — depth is never sacrificed to save tokens.

**Issues are exempt from the placement choice — they are deep-only by rule (AC-10).** An `ISS-` defect (`issues.md`/`issue-filter.md`) is report-only and **never eligible for the lean tier**, whatever its value or certainty. The lean `AGENTS.md` may carry at most a one-line pointer to the issue ledger, never an issue. So R9's "highest-value non-obvious facts go lean" applies to **context findings only**; the issue layer's placement is fixed (deep ledger + dashboard + SARIF), not decided per-finding.

## R10 — User-facing prompts: spec'd options only, no confabulation
Interactive decision prompts come ONLY from the spec'd pickers (the *Customize picker*, the *Translate picker*, the **one consolidated run-start prompt** — scope/effort · database · existing front-door file, `SKILL.md` *Run-start prompt* — and the emit-time existing-file confirmation in `generation.md`). The engine MUST NOT invent a prompt, an option, or a recommendation at runtime. Every option offered MUST map to a real, implemented behavior (an existing flag / strategy) — never a path the run cannot faithfully execute. **The recommended choice MUST equal the stated default**; if a run ever has a principled reason to deviate, it states that reason in one plain sentence — it NEVER shows two competing "recommended"/"default" tags on different options, and never recommends a path that contradicts the product's own positioning. When unsure how to present a choice, present **fewer, real** options — never a fabricated one.

**Plain language, always — no internal vocabulary (R10-plain).** Beyond honesty, every label, header, and option body a user sees MUST be plain words they can act on without knowing DeepInit's internals. NEVER an internal code — an issue-family code (`IF-*`), an `AF-*`/`AC-*`/`DP-*`/`WF-`/`BR-` code, or a rule ref shown as such (e.g. "the R7 gate", "B3"). NEVER implementation-mechanics jargon — *review cycles*, *depth=fast/thorough/deep*, *grep-first*, *deep extraction*, *(cost) ceiling*/*preflight*, *Wave 0a*, *managed-/owned-region*, *lean/deep tier*, *SARIF*, *ORM-drift*, *live-drift*, *information_schema*, *EF migrations*, *NPoco*. **Say the OUTCOME, not the parameter** — "a faster, cheaper pass", not "depth=fast / 0 review cycles"; "I found a database — read it live to check the real schema?", not "Database analysis for ORM-drift (IF-2)?". The internal name may live in the deep/technical docs; it must never reach a button. The deterministic banned-term mirror is `tools/prompt_ux.py` `BANNED_TERM_PATTERNS` / `prompt_jargon_hits()`, and harness §95 scans every spec'd prompt option against it. This is the user-prompt analogue of R1 (never fabricate) and AF-1 (when uncertain, omit): a confidently-wrong OR jargon-dense prompt erodes trust exactly like a confidently-wrong finding.
