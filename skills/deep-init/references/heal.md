# heal.md — C-HEAL (governance over `--lint` / `--update` / `--update-adr`)

Heal is a **governance wrapper** over DeepInit's existing maintenance primitives — **not a new subsystem** (S-7). It risk-tiers what maintenance is safe to automate, drives the issue lifecycle off the baseline diff (`update.md`), and **defaults to writing nothing**. **Read `update.md` (baseline + DP-1 + Step-4) and `verification.md` first.**

## Report-only floor (HARDCODED — AC-11, the safety contract)
Even in `apply`/`auto`, heal **never modifies a source file**. The only writable paths are `.ai/` outputs + the `AGENTS.md` owned-region (`DEEPINIT:START/END`) + `.bak` backups. This floor is hardcoded in the procedure, **not** a config knob: **config may TIGHTEN heal, never LOOSEN it**, and behavioural / business-rule heals are **always staged for manual review even under `auto`**.

## Risk tiers
- **auto-safe** (mechanical, no semantic judgement): a moved file → re-resolve the citation (reuse `verification.md` Pass-1 `SYMBOL_MOVED`); a renamed symbol → update the cited line; a `resolved` issue → retire it from the open ledger. These touch only doc citations/state — never meaning.
- **flag-semantic** (needs human judgement — **never auto-applied**): a BR whose implementing code changed → re-verify, flag if it no longer holds; a new contradiction (IF-4); a regressed issue. Surfaced for review, never silently edited.

## Modes (`--heal=`)
- `detect` — report what heal WOULD do (rides the zero-token `--lint` staleness where possible); no writes.
- `preview` **(DEFAULT)** — a dry-run diff of the auto-safe fixes + the flagged-semantic list; **writes nothing**.
- `apply` — apply **auto-safe fixes only**; flag-semantic items are listed, never applied.
- `auto` — apply auto-safe across the blast radius; flag-semantic items are **still only flagged** (the floor holds). `--heal-confidence=N` raises the bar before auto-acting.

## Scoping + loop-stability
Heal hangs issue re-detection off `update.md` **Step-4 (always-re-run-horizontal)** — horizontal scope, never a parallel cross-component scan — and maps the DP-1 dirty set to **affected issues** (those whose provenance `file:line` falls in a dirty component): a join over existing data, not a new traversal. **Loop-stability (two-strike):** require recurrence across runs / a confidence threshold before auto-acting, so a flapping detection never thrashes the ledger. The flag-semantic recheck is **not** zero-token and lives on the `--update` path only — `--lint` stays zero-token.

## Routing
Heal outcomes surface in `changelog.md` (the issue section), the dashboard, and the **CI exit code** — a local tool, **no external notifier** (suite boundary).

## Tests (AC-4 / AC-5 / AC-11 — metamorphic, deterministic; built with the harness extension in Wave 6/T6.3, provable for the logic introduced here)
- accept an issue → next run it is NOT "new"; resolve (remove the code) → `resolved`; reintroduce → `regressed` in the changelog.
- `preview` writes nothing — assert no file **content-hash** change.
- `auto-safe` applies ONLY mechanical citation/line fixes; a semantic item is flagged, never applied.
- a line-shift-only refactor does NOT flip a still-open issue to `resolved`/`new` (match-key stability).
- `--heal=auto` source-immutability: snapshot source-file **content hashes** before/after; assert ZERO source file changed (only `.ai/` + owned-region + `.bak`) — exercises the highest-risk mode, not just preview/apply.
