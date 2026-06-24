# adr.md — Decisions & Knowledge Log

Extracts the *why* — architectural decisions and accumulated insights. The purest non-inferable content (an agent can read *what* the code does but never recover *why* from code alone), so these are first-class (D2-015). Two entry modes plus inline aggregation during a full run.

## ADR extraction
During a full run, each component's **Design Rationale** (extraction §11) feeds here; this stage aggregates them and mines additional system-wide decisions into `.ai/docs/decisions.md`.

**Where to look (heuristics):**
- Code comments with decision language: `because`, `decided`, `chose`, `instead of`, `to avoid`, `workaround`, `note:`, `historically`, `TODO`/`FIXME` explaining a tradeoff.
- `git log`/blame around refactors and large diffs (commit messages stating rationale).
- README / docs / existing ADR folders.
- Intentional patterns: a non-default library choice, a custom implementation where a standard one exists, an unusual data shape — each implies a decision.

**ADR record:**
```markdown
## ADR-{nnn}: {title}
- **Status:** accepted | superseded | deprecated
- **Date:** {ISO or "unknown — inferred"}
- **Context:** {the forces / problem}
- **Decision:** {what was chosen}
- **Why:** {rationale}
- **Evidence:** {file:line / commit / comment}
- **Consequences:** {tradeoffs, what it constrains}
- **Certainty:** [HIGH|MEDIUM|LOW]
```
**Heading shape (both accepted).** The canonical example above is `## ADR-{nnn}: {title}`; DeepInit's own deep-tier ledger renders ADRs one level deeper as `### ADR-{nnn} — {title}` (an em-dash, sitting under the decisions-doc structure). Both forms are valid — `tools/build_docs_viewer.py` `parse_decisions` is **tolerant of either** (`## ADR-N:` and `### ADR-N —`), and the report/viewer render them identically (the parser is the one source of truth; ISS-010).

Only emit an ADR above a confidence threshold (clear evidence of an intentional choice). Speculative "maybe they chose X" → Open Questions, not an ADR.

## Knowledge Log
Classify insights/gotchas surfaced during analysis into the 8-category taxonomy, `KL-{category}:{nnn}`:
`progress` (state of work) · `learning` (non-obvious thing discovered) · `architecture` (structural insight) · `solution` (a fix/approach that works) · `mistake` (a known wrong path / anti-pattern present) · `integration` (how parts connect) · `debug` (a tricky diagnosis) · `preference` (a convention the codebase follows).
Each: `KL-{category}:{nnn} | insight/gotcha | file:line | certainty`. High-value KLs are promoted to the lean root by the Filter; the full set lives deep.

## `--decisions-only`
Fast path (~5 min, minimal tokens): skip full component analysis; grep the decision-language patterns above + read README/docs + scan git messages; produce/refresh `decisions.md` and the Knowledge Log only. For when the user wants the *why* captured without a full run.

## `--update-adr`
Re-check existing ADRs against current code (no full re-analysis):
- **CONFIRMED** — the decision still holds; evidence still present.
- **DRIFTED** — code has moved away from the decision (flag: decision says X, code now does Y).
- **EVIDENCE-MISSING** — the cited evidence (`file:line`) no longer resolves; re-locate or downgrade certainty.
Append results to `decisions.md`; note drift in `changelog.md`.
