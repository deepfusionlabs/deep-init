# review.md — Iterative Refinement Cycles

The quality-improvement loop. **Two modes only:** **`fast` = 0 cycles** (skip review); **`thorough` (the default) = 2 cycles, then an *adaptive* 3rd ONLY IF the cycle-2 quality gate still fails** (see *Adaptive third cycle* below). There is **no cycle-count knob and no forced-max mode** — the default self-escalates when, and only when, the work is not yet clean, so nothing needs configuring. Distinct from `verification.md` (which is mandatory citation-existence, always on) — review *improves the analysis*; verify *checks the citations*. Skip entirely in `fast`.

Each cycle = R1 critique → R1.5 validate → R2 investigate → R3 reconcile.

## R1 — Adversarial critique
A single Task subagent with **fresh context** and a different objective than the creators: creators document what exists; the critic finds what is WRONG, MISSING, or INCONSISTENT. Input: all `.ai/docs/current/` files. Output: `reviews/cycle-{n}-critique.md`.

**5 review types:**
1. **Completeness** — per component, count (grep) route/controller actions vs documented `WF-`, models vs data models, validations vs `BR-`, external calls vs `IP-`. Flag gaps. Check mandatory sections non-empty/justified.
2. **Consistency** — cross-check: A says it calls B → does B list A as a caller? `WF-001` says "Auth validates role" → does Auth have a matching `BR-`? domain-model entity → entity-table mapping exists? `IP-` outbound call → edge in technical-dependencies? schema tables → all in entity-table mapping?
3. **Depth** — sections <3 sentences where the component has >30 files; important findings still `[LOW]`/`[MEDIUM]`; workflow traces with "unclear"/"..."; `BR-` without `file:line`; components with much less depth than peers.
4. **Missing connections** — `BR-` not referenced by any workflow; workflows not covered by any rule; entities without relationships; integration points without workflow steps; stored procs not mapped to a component.
5. **Conflict** — two components "own" the same entity; workflow step order contradicts code; component `BR-` contradicts system `DR-`; architecture style contradicts component patterns; DB relationship not in code models.

**Critique output:** a severity-sorted table `CR-{nnn} | type | severity (CRITICAL/HIGH/MEDIUM/LOW) | location | issue | investigation task`, a summary (counts + top concern), and a recommended investigation order.

## R1.5 — Validate (find → validate → filter)
Parallel subagents, one per CRITICAL/HIGH issue. Each goes **back to the code** to confirm the issue is real before tokens are spent investigating: returns `{CR-id}: CONFIRMED | FALSE_POSITIVE | NEEDS_CONTEXT — {reason}`. Filter: CONFIRMED → R2; FALSE_POSITIVE → drop (note why); NEEDS_CONTEXT → downgrade to LOW, carry forward.

## R2 — Targeted investigation
Parallel Explore subagents, one per confirmed issue. Each performs the specific investigation task (reading **code**, not just prior outputs) and writes an addendum to the relevant `.ai/docs/current/` file:
```markdown
<!-- Review Cycle {N} Addendum — CR-{nnn}: {files read}; {summary} -->
### Addendum: {topic} (Review Cycle {N})
{detailed findings with file:line}
```
MEDIUM/LOW issues → appended as "Known Gaps" (acknowledged, not investigated).

## R3 — Reconciliation
Inline. Verify each CRITICAL issue is resolved (check addenda); update `cross-references.md`; re-check consistency; compute the quality score. Output: `reviews/cycle-{n}-reconciliation.md`.

**Quality score:**
| Metric | Target |
|--------|--------|
| Route coverage (workflows documented / controller actions grep) | >80% |
| Model coverage (entities documented / model classes grep) | >90% |
| Cross-ref consistency (verified / total) | >95% |
| Avg certainty | HIGH |
| Critical issues remaining | 0 |

**Three-facet evaluation (DocAgent ACL 2025), 1–5:**
- **Completeness** — all structural elements documented (routes, models, integrations)?
- **Helpfulness** — could a developer fix a bug using only the generated docs?
- **Truthfulness** — spot-check 10 claims against source code; all verified? (Complements C6 existence-checking with correctness sampling.)

Recommendation per cycle: `Run next cycle | Proceed to generation`.

## Adaptive third cycle (the default `thorough` escalation)
The default mode `thorough` runs **2 cycles, then evaluates the cycle-2 R3 quality gate** and runs a **3rd cycle automatically — and only — if the gate still fails**, i.e. ANY of:
- **CRITICAL issues remaining > 0** (an unresolved CRITICAL after cycle 2), OR
- **route coverage < 80%**, OR **model coverage < 90%**, OR **cross-ref consistency < 95%** (the R3 targets above).

Otherwise **STOP at 2** — the analysis already clears the gate, so a 3rd pass would be polish with diminishing returns (~10%, an unmeasured estimate). The principle: *focus on 2; spend the 3rd cycle only when the work is not yet clean.* This needs **no configuration and exposes no knob** — it is simply what a bare `deep-init` does. The only other review setting is `fast` (`/deep-init:fast`), which skips review entirely for a quick, cheap pass; there is deliberately no way to *force* or *cap* the cycle count, because the gate already does that better than a hand-set number. Record the escalation decision **and the gate values that drove it** in `reviews/cycle-2-reconciliation.md` so the choice is auditable (R1: no silent caps). *(How often the 3rd actually fires on real repos is an open calibration question — these thresholds escalate only when it materially matters, not on cosmetic gaps.)*

## Cycle focus + diminishing returns
| Cycle | Focus | Typical lift |
|-------|-------|--------------|
| 1 | major gaps + conflicts | ~40% |
| 2 | depth + accuracy | ~20% |
| 3 | polish + completeness | ~10% |

Report the quality score after each cycle so the user can decide whether to continue.
