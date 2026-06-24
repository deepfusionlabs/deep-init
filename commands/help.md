---
description: Show all DeepInit commands + key options, grouped and ordered by how often you'll use them. Instant, no analysis.
---

Print the DeepInit command overview **exactly** as below — a static reference card, NOT an analysis (no file reads, no detection, no tokens spent on the repo). Render it verbatim, then stop:

---

**DeepInit — what you can run** (start with a bare `/deep-init`; it already runs at max quality)

**Everyday**
- `/deep-init` — full run at max quality: **2 adversarial review cycles, plus an automatic 3rd if the analysis isn't yet clean** + deepest analysis + issues + report + SARIF.
- `/deep-init:fast` — quick pass: review cycles skipped (0), faster and cheaper.
- `/deep-init:refresh` — refresh only what changed since the last run.
- `/deep-init:translate` — emit the report in another language (Spanish · Chinese · Portuguese · Russian · Japanese · German · French · Hebrew, or any other) — opens a language picker; English stays canonical.

**Check & tune**
- `/deep-init:check` — "is it still true?" 0-token staleness + broken-citation audit (add `--status` for the fast hash-only subset).
- `/deep-init:customize` — tune the run with **buttons** (depth · issues · outputs · scope · cost · hooks) — no flags to type.
- `/deep-init:doctor` — preflight: tools, scope, resolved config, enabled families (0 tokens); offers to install the freshness hooks.

**Reference**
- `/deep-init:version` — which DeepInit version is actually running (and whether you need to `/reload-plugins`).
- `/deep-init:plugin-update` — update DeepInit to the latest version (one confirm) and guide the reload.
- `/deep-init:help` — this overview.

**Power users:** every option is also a `--flag` (see the skill's reference), a key in the schema-validated `.ai/deepinit.config`, or just plain English — *"do a quick pass, skip the database."* Nothing needs to be memorized.

---

After printing, take no further action unless the user asks.
