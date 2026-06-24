# verification.md — C6 Verifier (citation-existence)

A mandatory pass over every finding that survives the Filter, on **both** tiers. It makes the output trustworthy: every claim carries a citation that resolves and plausibly supports it. This is the v1.0 anti-hallucination control — cheap, deterministic where possible, and always on.

## Two passes (per surviving finding)

### Pass 1 — Existence (deterministic, zero LLM tokens)
For every `file:line` in a finding's provenance:
- The file exists on disk.
- The line number is within the file's current length.
- (Where a symbol is named) the cited line still contains the referenced symbol/construct (cheap grep around `±3` lines).

Result per citation: `RESOLVES` | `FILE_NOT_FOUND` | `LINE_OUT_OF_RANGE` | `SYMBOL_MOVED`.

**Citation path form — full repo-relative, normalized before the check (LESSON 1).** Every emitted citation MUST be a **full repo-relative path** (`skills/deep-init/SKILL.md:42`, never a bare `SKILL.md:42`); the extraction subagents emit from their component's scope, so a bare basename is the easy mistake (the 2026-06-15 dogfood emitted ~1184 bare paths that had to be hand-normalized before this pass would resolve). Two enforcers, belt-and-suspenders: (a) the emitter/extraction prompt **prefixes every citation with the component's full repo-relative path** (`generation.md`); and (b) before the existence check the Verifier **normalizes** any bare basename to its **unique** repo-relative path (`tools/verify_citations.py` does this deterministically). A bare basename that is **ambiguous** (matches ≥ 2 files) is **flagged, never silently resolved** — the emitter must disambiguate with the full path.

**No line cites into inherently-shifting files (LESSON 1b).** A `file:line` into a file whose lines shift wholesale on a routine change — a regenerated doc (`CHANGELOG.md`, the `.ai/docs/` regenerated tier, `STATS.json`) or an append-mostly log — silently **rots**: after a version bump the citation still *resolves* but points at the **wrong content** (a resolves-but-lies hazard Pass 1's existence check cannot catch). Cite such files at **file level** (no `:line`) or pin a **stable heading anchor**; the Verifier surfaces a line-cite into a known-shifting file as a warning (`shifting_line_cites`, advisory — it never fails the gate, since the citation does resolve).

### Pass 2 — Plausibility (lightweight)
For each resolved citation, a quick check that the cited code actually *relates to* the claim — not a proof of correctness, just "does this location plausibly support this statement?" (e.g. a BR claiming a validation cites a line that contains a validation, not an unrelated import). Result: `PLAUSIBLE` | `WEAK` | `MISMATCH`.

## Handling
- All citations `RESOLVES` + `PLAUSIBLE` → `verified: true`, stamp `verified_at`.
- Any citation `FILE_NOT_FOUND` / `LINE_OUT_OF_RANGE` → **drop the citation**; if it was the finding's only provenance, **drop the finding from the lean tier** and flag it `[unverified]` in the deep tier (R1: prefer omission over a uncited claim).
- `SYMBOL_MOVED` → attempt re-resolution by grepping the symbol in the same file; update the line if found, else treat as not-found.
- `WEAK`/`MISMATCH` plausibility → downgrade certainty one level and flag `[citation-weak]`; keep in deep, drop from lean.

## Scope honesty (state this in the output)
The Verifier guarantees a citation **exists** and is **plausible** — **not** that every claim is **correct**. Three layers, escalating, and what's in v1.0:
1. **Citation-existence + plausibility** — *this stage, mandatory, every run.* ✅ v1.0.
2. **Three-facet Truthfulness spot-check** — `review.md` spot-checks ~10 claims against source per cycle (mode-gated). ✅ v1.0 (in thorough — incl. the adaptive 3rd cycle).
3. **Cross-model claim-correctness** — re-deriving claims with a second model (AgentAlliance) to de-correlate single-model error. **ROADMAP, not v1.0** (D2-019): gated on AgentAlliance integration-readiness (≥1 month). v1.0 has **no dependency** on AgentAlliance. Findings carry a `cross_model_agreement` field reserved for when it lands; it is unset in v1.0.

## When it runs
Always, after Filter and before Emit. It is not skippable (unlike review cycles, which are mode-gated). The `--lint` staleness path reuses Pass 1's existence check to detect broken references between runs (see `update.md`) — the same deterministic mechanism, zero tokens.

## Output annotation
```
{id} | verified: {true|false} | verified_at: {ISO} | citation_status: {RESOLVES|…} | plausibility: {PLAUSIBLE|WEAK|MISMATCH} | cross_model_agreement: (unset in v1.0)
```
`generation.md` emits only findings whose `verified_at` is set into the lean tier; the deep tier may include `[unverified]`/`[citation-weak]` findings, clearly marked, so nothing is silently dropped.
