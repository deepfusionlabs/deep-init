# Changelog

All notable changes to DeepInit are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses **manual** `0.x`
versioning (no release tooling derives this file).

## [0.7.1] — 2026-07-01

### Changed
- _Summarize this release; replace this line._

---

## [0.7.0] — 2026-06-30

### Changed
- _Summarize this release; replace this line._

---

## [0.6.0] — 2026-06-27

### Changed
- _Summarize this release; replace this line._

---

## [0.5.1] — Security reporting + output copy

- **Security** — vulnerability reports can now be filed through GitHub Private Vulnerability
  Reporting (the repo's **Security → Report a vulnerability** tab), alongside email.
- Clearer `version` and `plugin-update` command output.

## [0.5.0] — Initial public release

The first public release of **DeepInit** — a Claude Code skill that reads a codebase and emits a
grounded, verified, two-tier agent context layer (a lean `CLAUDE.md` + a deep `.ai/docs/` layer),
every claim tied to a `file:line`, plus a report-only issue layer. 100% local, read-only, MIT.

Developed and dogfooded internally at DeepFusion Labs before this first public release.

- **Two-tier context** — a lean, always-loaded `CLAUDE.md` + an on-demand `.ai/docs/` deep layer
  (per-component analysis, whole-system docs, decisions/ADRs, live DB/ORM drift).
- **Grounded + verified** — every emitted claim cites a real `file:line` and is checked against the
  code before it is written (never fabricate).
- **Report-only issue detection** — 10 detector families + a class-conformance census, each gated on
  its own measured false-positive control; findings live in the deep ledger and a SARIF export, never
  in the lean tier, and never edit your source.
- **One offline report** — a single self-contained `.ai/report.html` (Docs · Insights · Map) plus a
  SARIF v2.1.0 export; `/deep-init:translate` localizes it.
- **Incremental refresh** — `/deep-init:refresh` re-analyzes only an edit's blast radius; a 0-token
  staleness + broken-citation check via `/deep-init:check`.
- **Tested like production software** — a deterministic, no-LLM validation harness is the only test,
  with a mutation meta-harness proving every gate is load-bearing; CI runs it on every change.
