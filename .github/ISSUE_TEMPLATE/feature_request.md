---
name: Feature request
about: Suggest a new detector, language, stage improvement, or output
title: "[feat] "
labels: enhancement
---

**The problem**
What's missing or hard today? Lead with the problem, not the solution.

**Proposed change**
What you'd like DeepInit to do. If it's a new **detector**, describe the defect class and — crucially — how it
would stay **precise** (what would keep it from crying wolf). A detector ships only with a measured
false-positive story.

**Scope check**
DeepInit is deliberately scoped: grounded, verified context + report-only issues, 100% local. It is **not** a
graph-UI, a dedicated security scanner, or a cross-model orchestrator. Does your request fit that scope?

**Would you contribute it?**
A new detector/rule needs a `mini-*` fixture + a harness section + a killing mutation (see CONTRIBUTING.md).
Happy to help if you want to take it on.
