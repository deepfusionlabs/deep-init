---
description: Tune a DeepInit run with buttons — depth, issue detection, outputs, scope, cost, and the freshness/notification settings (disable the nudge, change its cadence/time-window) — no flags to type. Opens a native multiple-choice picker, then runs.
---

Run the **deep-init** skill in **interactive customize mode** (equivalent to `--interactive`). Load `skills/deep-init/SKILL.md`.

BEFORE any analysis, collect the run settings as **type-safe button choices** using the **AskUserQuestion** tool — the "Customize picker" flow in SKILL.md — so the user never hand-types a flag. Ask only the high-value questions (each Enter-skippable, keeping the max-quality default):

1. **Depth & speed** — Deep (default) / Thorough / Fast
2. **Issue detection** — All families (default) / Core only (IF-1…IF-5) / Off
3. **Outputs** — Report (Docs+Insights) / SARIF (multi-select; both on by default)
4. **Scope** — Whole repo (default) / Pick components
5. **Cost ceiling** — $25 (default) / $50 / Custom
6. **Freshness & notifications** — Keep defaults / Configure… / Turn the nudge off / Pause in this repo

Question 6 governs the proactive freshness surfaces (the SessionStart staleness nudge + commit breadcrumb / auto-update). Unlike 1–5 it controls *future* behavior, so on **Configure…** drill into a short follow-up `AskUserQuestion` (session-start nudge on/off · cadence session/window/always + window-hours · commit breadcrumb · auto-update · install the commit hook) and — per the SKILL.md *Freshness controls* spec — **persist** the chosen freshness keys ONLY on an explicit confirmation, via the surgical schema-validating writer (`python "${CLAUDE_PLUGIN_ROOT}/tools/freshness_config.py" --root <repo> --set <key>=<value> --apply`; **Pause in this repo** writes `.claude/.deepinit-no-nudge` instead). This is the one narrow exception to "a run never writes `.ai/deepinit.config`" — never hand-edit, never write without the user's "yes".

Then resolve the effective settings (max-quality defaults ← `.ai/deepinit.config` ← the picker answers), echo the one-line resolved panel, and run the full pipeline. Anything the picker does not cover stays available in `.ai/deepinit.config` (schema-validated) or as a flag.

$ARGUMENTS
