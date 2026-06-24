# dashboard.md — C-DASH (self-contained dashboard, full build)

Emits one **`.ai/dashboard.html`** — a navigational view over DeepInit's grounded truth + the issue ledger. *(Superseded by the unified C-REPORT `.ai/report.html` — `report.md`, ADR-019 — which renders this as its **Insights** view; this C-DASH spec stays legacy until the cutover.)* **Read `redaction.md` first:** the embedded data passes through redaction before it is written into the file.

## Hard constraints (AC-7 / AF-6 / S-8)
- **One self-contained file.** Vanilla JS + **inline** CSS. **NO framework, NO CDN, NO external `src`/`href`, NO network calls of any kind.** Any tiny helper is vendored inline. (License-clean precisely because nothing third-party is bundled — AF-6.)
- **Navigational only** — it reads pre-computed data; it performs **no analysis** and reaches no network.
- **A ranked/heatmap view, NOT a dependency-graph explorer** — the interactive graph stays DeepMap's territory (S-8).
- **Generated, not hand-edited.** R3 provenance comment at the top; regenerated every run; **no owned-region protection** (unlike `AGENTS.md`) — state this in the file so no human edits it expecting persistence.
- **Default-on is gated** behind a build-time assertion that the emitted HTML contains **zero external/CDN references and zero bundled third-party code** (the license clearance was conditioned on this — AF-6). If the assertion fails, do not emit / do not default it on.

## Data (embedded, redacted)
The skill injects ONE redacted JSON blob at a clearly-marked placeholder in the template (`skills/deep-init/assets/dashboard-template.html`). Shape:
```json
{
  "project": { "name": "...", "architecture": "...", "generated": "{ISO}", "run_id": "..." },
  "components": [ { "name": "...", "criticality": "Core|Supporting|Peripheral", "risk": 0.0, "churn": 0, "bus_factor": 0, "coverage": 0.0 } ],
  "issues": [ /* the §4.1 issue records from .ai/docs/issues.md (verified only as confirmed; [unverified]/[citation-weak] clearly marked) */ ],
  "drift": [ /* IF-2 rows: entity, table, field, orm, db, drift, severity */ ],
  "decisions": [ { "id": "ADR-…", "title": "...", "status": "CONFIRMED|DRIFTED" } ],
  "counts": { "open": 0, "resolved": 0, "regressed": 0, "by_severity": {} }
}
```
**Redaction runs over this blob before embed** — file:line + metadata only, never raw source or secrets.

## Panels (§5.3)
1. **Grounded-truth overview** — project, component list, architecture style; the headline counts; an honesty line (report-only · 100% local · flags-likely-not-proven · measured-own-FP).
2. **Issue triage board** — issues grouped by **severity × family**, each row showing `file:line`, the flag-don't-assert explanation, certainty, and lifecycle (new/persisting/accepted/resolved/regressed). **Filter/sort by family / severity / component.** **Default visible filter = `medium`+** (Low available behind a toggle) — the ledger/SARIF still withhold nothing; this only keeps the human-facing surface from leading with the noisiest, lowest-certainty findings (anti-alert-fatigue; the ledger is the complete record).
3. **Risk heatmap (IF-5)** — components ranked by risk score (`priority = f(severity, criticality, churn, bus_factor, coverage)`); a ranked table / heatmap, **not** a graph explorer.
4. **DB-drift panel (IF-2)** — the drift rows (entity ↔ table ↔ field, ORM-says vs DB-says, severity); a clear "live-verified vs unverifiable (run with --db)" state, never a phantom-drift claim. *(Tri-state status — configured / live-verified / unverifiable — is shown ONLY where verifiability genuinely varies: this IF-2 live-vs-static distinction, and the semantic families' certainty tags. Deterministic static detectors are simply "computed" and carry no tri-state ceremony — don't impose the vocabulary where the value never changes.)*
5. **Decisions / WHY** — ADRs + their CONFIRMED/DRIFTED status (the IF-4 surface).

## Template
`skills/deep-init/assets/dashboard-template.html` carries the markup + inline CSS + vanilla-JS rendering/filter/sort logic and a single data placeholder the emitter replaces with the redacted JSON. Self-containment is asserted at emit (grep the output for `http(s)://`, `cdn`, external `src=`/`href=` → must be zero).
