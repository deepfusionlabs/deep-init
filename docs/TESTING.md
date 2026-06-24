# DeepInit — Testing Layers (what to run, and when)

DeepInit's tests span wildly different cost/speed/determinism profiles — from a ~7-second
deterministic check to multi-hour real-LLM runs. Running *everything* on every change is wasteful
and slow; running too little ships regressions. This doc defines the **four layers**, the exact
command for each, and the **convention for when to run each** — so a one-line doc fix doesn't trigger
a 16-minute mutation sweep, and a release never skips one.

> **The one rule:** the costlier the layer, the rarer + more deliberate its trigger. The deepest
> layer (real tokens) fires only when the engine's *output* could actually have changed, or for a
> release — never for plumbing.

---

## L0 — SMOKE  ·  ~7 s · 0-token · run on EVERY edit

The deterministic harness alone — keeps the tree green as you build.

```
PYTHONUTF8=1 python tests-fixtures-v1/_chat_validation.py      # → N/N PASS
```

Even lighter (no test run — dirty-tree + working-tree secret scan): the `oss-validate --fast`
checkpoint. Use L0 continuously; never carry a red tree into the next edit.

## L1 — GATE  ·  ~10–60 s · 0-token · run before a commit / at a phase boundary

Harness + the drift guards + **only the mutations whose target files changed** (not the full sweep).

```
PYTHONUTF8=1 python tests-fixtures-v1/_chat_validation.py
python tools/check_stats_drift.py
PYTHONUTF8=1 python tests-fixtures-v1/_mutation_harness.py --changed   # mutations for files in `git diff` only
```

Proves the gates you touched are load-bearing and the counts/docs are reconciled, without paying for
the full mutation sweep. (`--changed` keys off `git diff --name-only`; falls back to a named subset
via `--only/--start/--count`.)

## L2 — FULL / RELEASE  ·  ~15–20 min · 0-token · run before a version bump / merge to main / in CI

The complete deterministic net: harness + stats-drift + count-drift + **ALL** mutations + the
public-harness contract.

```
python tools/validate_all.py            # --fast skips the public-harness re-run
```

CI runs this on every push to `main`. **Mandatory** before any release and before merging to `main`.
Run it in the FOREGROUND, serially — never alongside another harness-mutating command (they race the
shared `validation/_harness_summary.json`), and never let a commit land while it's mid-run (a torn
tree). oss-kit's commit-guard backs this up (blocks a commit while `.oss-kit/.mutation-running` is held).

## L3 — DEEP / REAL-ENGINE  ·  minutes–hours · metered (tokens) · run when the ENGINE changes / before a major release / periodically

Exercises the **actual product** (a real Claude run of the skill), not the Python reference impls.
Two sub-layers (the integration framework's Tier-1 / Tier-2):

- **Tier-1 auditor — 0-token, CI-safe.** Re-derives coverage / faithfulness / citation-resolution /
  `deepinit_wrong_high` from the **committed** real-engine artifacts and demands they reproduce
  (turns a non-deterministic output into a deterministic audit).
  ```
  python tools/audit_integration_run.py
  ```
- **Tier-2 metered runner — real LLM, operator/periodic.** Drives deep-init on a pinned corpus clone,
  snapshots every emitted artifact, scores it, writes an `integration-run-record/v1` the auditor checks.
  ```
  DEEPINIT_REAL_ENGINE=1 python tools/run_integration.py --repo <name> --sha <40-hex>
  ```
  Env-guarded: without `DEEPINIT_REAL_ENGINE=1` it no-ops, so it can never fire (or spend tokens) in CI.

Run L3 **only** when `skills/deep-init/**` (the engine) changed — i.e., the real output could differ —
or for a release / a periodic re-validation. NEVER for a harness/docs/tool-only change: the engine
didn't move, so its output can't have.

---

## Clean-environment real-run (Codespaces) — the run-start-prompt eyeball

**Why a clean room.** L0–L2 pin the *spec'd* prompt wording byte-for-byte (the R10-plain contract +
the `prompt_ux`/`db_gate`/`emit_plan` decision logic — §95–§97), and they run in clean CI, so the
*wording* is guaranteed without any live run. The one thing a deterministic gate cannot see is whether
the **live engine obeys the spec template instead of improvising** under realistic host factors — and
the single biggest factor is an **installed MCP server** (e.g. a Postgres MCP, which is what made the
original DB prompt leak "ORM-drift (IF-2) … via MCP"). So the live confirmation is a *clean room*: the
**marketplace build** (not the dev checkout), no maintainer `~/.claude` (memory / other plugins / MCP),
and an explicit MCP on/off toggle. GitHub **Codespaces** gives that with no VM (`.devcontainer/`).

**Run it (per Codespace):**
```
# the .devcontainer postCreateCommand has already installed the Claude Code CLI + Python 3.13
claude                                                # authenticate: ANTHROPIC_API_KEY secret, or /login
/plugin marketplace add deepfusionlabs/deep-init      # the MARKETPLACE build, not this checkout
/plugin install deep-init@deepfusionlabs-deep-init
# reload, then open a target repo and run:
/deep-init
```

**Target repos** (each triggers a different run-start card; no new fixture needed):
- **Scope/effort card** → a genuinely large repo (clone any large OSS repo, or temporarily lower
  `--max-cost` to force it on a small one).
- **Database card + env picker** → a repo with one or several DB configs. `tests-fixtures-v1/mini-rails`
  already ships a `config/database.yml`; add a `staging`/`production` block to exercise the env picker.
- **Existing-file card** → drop a >200-line hand-written `CLAUDE.md` into the target before running.

**The matrix that matters:** `{no DB MCP} × {a Postgres MCP configured}` and `{ANTHROPIC_API_KEY (per-use $)} × {subscription /login}`.

**Acceptance (each run):**
1. **Exactly ONE** consolidated run-start prompt appears, showing **only the applicable cards** — never three scattered pauses.
2. **No internal vocabulary** on any label/header/body — no `IF-*`, no "the R7 gate", no "ORM-drift", "review cycles", "depth=", "SARIF", "managed-region".
3. The existing-file decision is **not re-asked** at the end (no double-ask).
4. A **production / managed-cloud DB host is auto-declined** to code-only (not offered as a live target); the §R7 y/n still fires for a live read.
5. The scope card leads with **scale/effort**, with the dollar figure a secondary line labeled pay-per-use — correct in both the API and subscription runs.
6. A small, DB-less, greenfield repo asks **nothing** (zero-friction preserved).

Capture a screenshot of the rendered prompt into the run log. This is the only check of the *rendered button text* in a live run.

### Layer-3 metered audit of the resolved cards (env-pending, by design)

Auditing *which cards the live engine resolved* (not the rendered text — that's the Codespaces eyeball
above) belongs to the **L3 Tier-2 metered runner**: a headless `--yes`/print run records the resolved
run-start cards into an `integration-run-record/v1`, and the 0-token **Tier-1 auditor** re-derives them
from the committed snapshot. Like every L3 Tier-2 metered run it is **env-gated** (`DEEPINIT_REAL_ENGINE=1`)
so it never fires or spends tokens in CI — the deterministic §95–§97 gates already pin the card *logic*,
so this is a periodic real-engine confirmation, run on the same cadence as the rest of L3.

---

## Activation matrix — which layers for which change

| Change                                                        | L0 smoke | L1 gate | L2 full        | L3 deep            |
|---------------------------------------------------------------|:--------:|:-------:|:--------------:|:------------------:|
| Docs / governance only                                        |    ✓     | drift only |     —       |        —           |
| A `tools/*.py` or a harness gate / fixture                    |    ✓     |    ✓    | before commit  |        —           |
| **Engine** edit (`skills/deep-init/SKILL.md` · `references/*.md`) | ✓     |    ✓    |       ✓        | ✓ (output moved)   |
| Version bump / release                                        |    ✓     |    ✓    | ✓ (mandatory)  | ✓ if engine changed|
| Routine minor fix                                             |    ✓     |    ✓    |       —        |        —           |

**Heuristic:** "Did the engine's *output* possibly change?" Only an edit under `skills/deep-init/**`
can answer yes → that's the sole everyday trigger for L3's token cost. Everything else is L0–L2.

## Why layered

- A minor tool/doc fix doesn't need a 16-min mutation sweep or a token-spending real-engine run —
  L0/L1 catch it in seconds.
- A release needs the full deterministic net (L2) so nothing regressed across the whole suite.
- An engine change is the only thing that can move the real product output, so it's the only everyday
  trigger that warrants L3's cost.

## How the layers map to the harness internals

- **L0–L2** are the deterministic suite (`tests-fixtures-v1/_chat_validation.py` §1…§N +
  `_mutation_harness.py`) — 0-token, the spec↔impl↔harness triple's safety net. Byte-stable, no LLM.
- **L3** is the real-engine integration framework: Tier-1 (deterministic audit of committed
  artifacts) + Tier-2 (metered runs). Its *records* (`integration-run-record/v1`, `coverage-record/v1`,
  the cost ledger's `cost.processing{}` timing) are themselves gated by the deterministic suite
  (§33/§34/§77…), so L3's machinery is L0–L2-tested even though its data comes from real runs.
