---
description: DeepInit preflight — tools, scope, resolved config (and whether it's valid), enabled issue families, estimated cost. 0 tokens, no LLM. Offers to install the freshness hooks.
---

Run the **deep-init** skill's **preflight report** (`--doctor`) — **0 tokens, no LLM, no analysis, no writes**. Load `skills/deep-init/SKILL.md` and report:

- **Version & freshness** — read `.claude-plugin/plugin.json` for the on-disk version; for the version actually *loaded* in this session (and a stale-reload check) run `/deep-init:version`. Claude Code loads plugin markdown once per session, so activation is host-dependent: in a plain terminal a new session (or `/reload-plugins`) picks it up; inside the VS Code/JetBrains extension you must **restart the IDE itself** — `Developer: Reload Window` does not reload the plugin host.
- **Tools detected** — scc, Graphify, ctags, a DB client, gitleaks/trufflehog (and what each falls back to if missing — nothing aborts a run).
- **Scope** — the component registry, whether a DB / git history is present and in scope.
- **Resolved settings** — the effective config (built-in max-quality defaults ← `.ai/deepinit.config` ← any flags), and whether `.ai/deepinit.config` is **valid** against `skills/deep-init/assets/deepinit.config.schema.json` (report unknown/invalid keys — warn, never fatal, R8).
- **Enabled issue families** and the **estimated cost** (base + issue-pass terms).
- **Freshness nudge — would it fire now?** Run `deepinit_status.py --explain` (0 tokens, no LLM) and show its verdict: docs stale or fresh, whether the SessionStart nudge is enabled or disabled (and by which switch), the cadence/window, the last-nudge state, and any active **[Not now]** decline-snooze. This answers "why am I not seeing the staleness nudge?" without guesswork.

Then **OFFER (do not auto-run)** to install the freshness triggers via `setup-hooks` — the `deepinit_status.py` keystone + the post-commit + SessionStart hooks (`references/triggers.md`) — and point to `/deep-init:customize` → Freshness to change the cadence / window or turn the nudge off. Make no changes.

$ARGUMENTS
