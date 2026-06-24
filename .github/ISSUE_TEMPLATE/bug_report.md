---
name: Bug report
about: A finding was wrong, a stage misbehaved, or the harness/output looks off
title: "[bug] "
labels: bug
---

**What happened**
A clear description of the problem. If DeepInit emitted a wrong or ungrounded claim, paste it.

**The grounding**
If it's about a finding: the `file:line` it cited and what the code actually says there. (DeepInit's
core promise is that every claim is grounded and verified — a wrong/ungrounded claim is the most serious bug.)

**Repro**
- Repository / language / size (rough LOC):
- Command / flags used:
- Stage where it went wrong (Detect / Extract / Filter / Verify / Emit / …):

**Expected vs actual**
What you expected, and what you got.

**Environment**
- OS:
- Python version (for the harness): 
- Graphify installed? (yes/no — it's optional; the skill falls back to ctags/grep)

**Anything else**
Logs, the relevant `.ai/docs/` snippet, or the `manifest.json` if helpful. Do **not** paste secrets — DeepInit
is local and never sees them, and neither should an issue.
