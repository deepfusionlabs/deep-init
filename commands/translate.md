---
description: Emit the DeepInit report in another language (report.<lang>.html) — opens a language picker (buttons), or pass a code. English stays the canonical analysis output.
argument-hint: "[es|he | other: <language>]"
---

Run the **deep-init** skill in **translate mode**. Load `skills/deep-init/SKILL.md` and follow `references/i18n.md` (read `references/report.md` first).

**If no language is given in `$ARGUMENTS`, open the language picker** — the *Translate picker* flow in SKILL.md, via the **AskUserQuestion** tool (buttons, no flag to type): the shipped targets (Spanish · Hebrew) as buttons + **Other**; choosing **Other** accepts **any language you type** (the `other: <language>` escape hatch — content translated, chrome falls back to English). Map the choice to a `--translate=<lang>` code.

Then:
1. Build/refresh the **canonical English** report first (`report.html`) — it is never altered.
2. Run the **content translation pass** over the report's prose fields into `.ai/i18n/translation_memory.json` (mask grounded tokens — code, `file:line`, record IDs, product nouns — translate, restore, verify; honest-degrade any miss to English).
3. Emit **`report.<lang>.html`** via `python tools/build_i18n.py <dir> --lang <code>` (deterministic; sets `<html lang dir>`, RTL for Hebrew; chrome is the template's baked `STRINGS` table picked by `<html lang>`).

English is always generated as the canonical output; translation is a derived overlay and never changes a grounded claim. Shipped languages: `es he` — any other language works on demand via `other: <language>` (chrome falls back to English, stated).

$ARGUMENTS
