# issue-filter.md — C-RAISE (raise-vs-suppress, the issue sibling of `filter.md`)

Where `filter.md` decides **placement** of context facts (lean vs deep), C-RAISE decides **raise vs suppress** for candidate issues. It runs after C-ISSUE detection (`issues.md`) and **upstream of verification** — no issue reaches Emit without passing both C-RAISE and C6. **Read `filter.md` and `review.md` first** (this stage reuses Test-3 from one and R1.5 from the other).

**Inputs:** candidate issue records from C-ISSUE (`issues.md` schema): `{family, claim, provenance[file:line], provisional severity, certainty, criticality}`.
**Output:** each candidate annotated `raise | suppress`, final `severity`, dedup-folded. **Suppressed candidates are dropped (not stored)** — unlike `filter.md`, which keeps demoted facts in the deep tier; an issue that fails the raise bar is not a finding at all.

> **Polarity flip — the governing bias (AF-1).** C-RAISE biases toward **suppression** — the *opposite* of `redaction.md`'s "when in doubt, redact." For issues, **when in doubt, do NOT raise**: a false-positive issue is the trust-destroying outcome; a missed low-severity issue is tolerable. This is the single most important control for the FP oracle.

## The tests (per candidate, in order — §5.2)

### Test-0 — Config-suppress? → suppress (spec §7)
Before any other test, apply the project's `.ai/deepinit.config` issue controls (`tools/issue_config.py`, gated by `_chat_validation.py` §46). Three controls, all optional, sensible defaults = nothing suppressed:
- **`issues-suppress`** — an FP-suppression LIST of `{path-glob, family}` entries (gitignore-style globs; `family: "*"` = all). A candidate whose `file:line` matches a glob AND whose family matches is suppressed (e.g. `{"path":"vendor/**","family":"*"}`, `{"path":"src/legacy/**","family":"IF-7c"}`).
- **`issues-language-toggles`** — per-language family on/off: `{"go":{"IF-8":false}}` turns a family off for that language only (the Go compiler already bans import cycles → IF-8 is structurally moot there).
- **`issues-baseline-accept`** — per-issue (OQ-3) accept: a list of baseline match-keys individually accepted, complementing the bulk `.issue_baseline.json`. An accepted key is suppressed; a sibling key at the same path/family still fires.

A config-suppressed candidate is **reported as a NAMED suppression with the rule that suppressed it** (R8 honesty — never silently dropped); it just never reaches the detection-effort tests below. Precedence: config-suppress → Test-1′ → … (config is the cheapest gate, so it runs first).

### Test-1′ — Linter-territory? → suppress
Anything a **linter / type-checker / SAST / formatter** would already catch (unused variable, a null-deref the type system flags, style, a known-CVE dependency) → **suppress** (DD-1…DD-3). DeepInit surfaces *grounded truth + the semantic/architectural problems a linter cannot see* — DB-vs-code drift, intent/decision contradictions, silent coupling, unenforced business rules, risk hotspots. It is **not** a linter and must not re-emit lint noise. Suppressed, not stored.

### Test-3 — Root-cause dedup (reuse `filter.md` STRUCTURE, issue-specific KEY)
Reuse `filter.md` Test-3's **collapse-and-anchor structure**, but with an **issue-specific dedup key = `(family, root-cause identity)` — NOT file co-location.** Collapse N candidates that share **one underlying cause** into one; keep the most specific `file:line` as the anchor (so the survivor still routes through verification Pass-1) and fold the rest into the reason.
> **Caveat (where "verbatim reuse" breaks):** never merge two **distinct** violations that merely touch the same file/module — *same module ≠ same root cause*. The dedup key for issues is the root cause, not the location.

### Test-2′ — Behavior/criticality → severity
Set final `severity` from behaviour impact × criticality (Core-unenforced-write = High/Critical; Peripheral → deep listing only, never ranked up). **ODC-style behaviour impact — never a borrowed vendor severity.**

## Forced FP-guard — R1.5 validate for the semantic families (make-or-break)
For **every raised SEMANTIC candidate (IF-1, IF-3a, IF-4, IF-7(a))**, run the `review.md` **R1.5 "Validate"** step **per issue, INDEPENDENT of review mode**: a fresh-context check goes **back to the code** and returns `CONFIRMED | FALSE_POSITIVE | NEEDS_CONTEXT`.
- `CONFIRMED` → keep raised.
- `FALSE_POSITIVE` → **suppress** (drop; note why).
- `NEEDS_CONTEXT` → downgrade certainty to `LOW`; for IF-1(a), **suppress** unless the entity+operation contrast is exact.

This validate is **forced** because `review.md` R1.5 is **mode-gated** (0 cycles in `fast`) — and `--issues` defaults **on** while `fast` is a one-word invocation, so relying on the review loop would silently disable the FP-guard in the most common token-saving mode. The per-issue validate is cheap and distinct from the full review loop. **IF-2 / IF-5 and the deterministic roadmap families (IF-8 cycle, IF-3b export-contract, IF-7's cross-boundary-swallow slice, IF-6's divergent-named-set slice, IF-10's const-fold dead-arm slices — both the in-file §25 form and the cross-module §29 form) skip it** — their grounding is structural (graph/DB/git/AST/set-algebra/const-fold, incl. the resolve-to-literal cross-edge fold that grounds to the origin const's `file:line`), not a semantic inference, so the empty handler / missing export / SCC / membership-difference / const-decided branch either holds or it does not; there is nothing for a back-to-code reasoning pass to confirm. (The *semantic* family **IF-7(a) error-path-contradicts-a-documented-rule (commission slice) SHIPPED 2026-06-09** and takes the forced validate exactly like IF-1/IF-3a/IF-4 — its R1.5 must re-check for a governing exception, parse the rule's required outcome, and scan the whole handler for re-raise/finally. The still-deferred semantic sub-cases — IF-7 (a-omission) + (b) unreachable-state, IF-6's same-logic-divergent-no-shared-name, and IF-10's system-level reachability headline (orphan exports / dead endpoints / cross-module flags) — DO take the forced validate when they ship.) Every raised issue carries **flag-don't-assert** wording ("possible … on path X").

## Class-conformance census overlay (additive, runs AFTER validate — never gates raise/suppress)
For every **raised IF-4(a) / IF-6 / IF-7(a)** issue (CONFIRMED for the semantic hosts) whose cited rule is **class-ranging** with a structurally-enumerable class and a decidable structural conformance check (see `issues.md` "Class-conformance census"), attach the **sibling-conformance census** + its signal. This is **deterministic and additive** — it **skips** the forced R1.5 (structural, nothing to confirm) and rides on a host fire that already passed C-RAISE (plus R1.5 for the **semantic** hosts IF-4(a)/IF-7(a); the **deterministic** IF-6 host passes C-RAISE only — it skips R1.5): **CORROBORATE** annotates "lone deviant among N (k conform)" and raises the issue's IF-5 `priority`/rank only (a strong-majority outlier — *never* certainty); **STALE** (N≥4, majority of the class also deviates) attaches a **neutral rule-health caveat** ("k of N also deviate — confirm de-facto-stale vs systemically-violated") and **changes nothing** (no priority/certainty/raise — so it can never bury a systemically-violated Core/security fire; the human adjudicates); **DEGRADE/NEUTRAL** leaves the issue unchanged. It raises **no** standalone issue and never flips a raise/suppress decision (provably zero recall/FP impact); a cardinality-1 / non-structural / N<3 / non-enumerable / aliased-base rule, and generated/test/vendored members, emit no census (degrade-don't-guess). Gated by `_chat_validation.py` §31 (hardened by the Run-14 adversarial review).

## Placement
C-RAISE is the issue-layer analog of `filter.md`, running after C-ISSUE detect and **upstream of `verification.md`** (nothing reaches Emit unverified). It does **not** touch `filter.md`'s lean/deep placement of context facts — issues are a separate stream and **never enter the lean tier** (R9 / S-3); the lean root gets only the one-line "Where to look → issues" pointer.

## Then: verification routing (every raised issue → `verification.md`, unchanged)
Each raised issue is routed through `verification.md` (Pass-1 existence + Pass-2 plausibility) and stamped with R1 certainty / `verified_at` — **call it, do not modify it**:
- citation `FILE_NOT_FOUND` / `LINE_OUT_OF_RANGE`, and it is the only provenance → **drop from any surfaced tier**; flag `[unverified]` in the deep ledger — **never surfaced as verified** (AC-6).
- `SYMBOL_MOVED` → re-resolve by grepping the symbol (the same primitive the baseline match key uses); update the line or treat as not-found.
- `WEAK` / `MISMATCH` plausibility → downgrade one certainty level + `[citation-weak]`; deep ledger only.
- **IF-2 asymmetry:** the ORM-side `file:line` is Pass-1 verifiable; the **DB object name is R7-gated live-read provenance, not citation-verifiable** — verify the ORM side and carry the DB name as provenance-by-live-read.

Scope honesty in Emit (`generation.md`): issues are framed **"likely / possible," never "this IS a bug"** (D2-019). Only `verified` issues reach the dashboard/SARIF/ledger as confirmed; `[unverified]`/`[citation-weak]` stay clearly marked in the deep ledger so nothing is silently dropped.

## Refuted-candidate count (transparency — reuses the existing R1.5/AF-1 outcomes, NOT a new control)
C-RAISE tallies the **refuted-candidate count** — candidates dropped by the AF-1 guard or by the forced R1.5 `FALSE_POSITIVE`/`NEEDS_CONTEXT` verdict — and surfaces it in the run summary as **"N considered · M raised · K refuted."** This is additive accounting layered over the verification primitive already invoked above (no second verify pass): it makes the suppression work visible — evidence the precision bias is doing its job rather than the detector simply never reaching the candidate. (The Wave-1 blind ledgers' `suppressed[]` arrays are exactly this set; see `_wave1_ledgers.json`.)
