# filter.md — C4 Non-obviousness Filter (the differentiator)

The stage that turns the ETH finding into the product. Comprehensive generated context *hurts* agents on most repos because it duplicates what the agent already reads; context helps only when it's **minimal and non-obvious**. The Filter decides, per finding, what reaches the lean always-loaded tier — and what an agent could already infer for itself.

**Inputs:** every finding from `extraction.md` (BR/WF/IP/data-models/legacy/rationale), `database.md` (ORM-drift), `adr.md` (ADR/KL), and `horizontal.md` (DR/UC/WA/cross-refs). Each finding has `claim`, `provenance [file:line]`, `certainty`.
**Output:** the same findings, each annotated with `non_obvious: true|false`, a one-line `reason`, and a `tier: lean | deep | drop-from-lean`.

> **R9 governs everything here: this stage decides PLACEMENT, never deletion.** Only trivially-inferable noise is dropped *from the lean tier*; it still lives in deep if useful. Non-obvious findings are never lost — at worst mis-placed. When in doubt, keep in deep.

> **Issues (`ISS-` records) are NOT findings this stage places (AC-10).** The Filter routes context findings (BR/WF/IP/data-models/legacy/rationale/ORM-drift) lean-vs-deep. An `ISS-` defect (from `issue-filter.md`) is **report-only and deep-tier only — it can NEVER be assigned `tier: lean`**, regardless of value or certainty. The lean `AGENTS.md` carries at most a one-line "Where to look → issues" pointer (`generation.md`), never an issue itself. Where a single underlying fact is both a lean *context fact* and an `ISS-` *defect*, the fact may be lean but the defect stays deep — deduped, never cross-contaminated.

## The three tests (run in order, per finding)

### Test 1 — Inferability
*Could a competent coding agent reading this repo derive this fact on its own, without being told?*

**INFERABLE → drop from lean** (the agent already gets this for free by reading the code):
- Derivable from a signature, type, or parameter list (`createUser(email, password)` does what it says).
- Derivable from a name following convention (`UserController`, `OrdersRepository`, `validate_email`).
- Derivable from an explicit import / dependency already visible in the file.
- A standard framework convention the agent knows (Rails REST routes, FastAPI dependency injection, Express middleware order) used in the standard way.
- A restatement of file/directory structure the agent can list.

**NON-INFERABLE → keep:**
- Requires **cross-file reasoning** (a constraint enforced in file A that governs behavior in file B).
- Depends on **runtime / DB / config state** not visible in source (the live ORM-drift; an env-driven branch).
- Requires **external or domain knowledge** (a business rule like "invoices over ₪10k need dual approval").
- Encodes **historical rationale** — *why* it's built this way (the purest non-inferable content; an agent can read *what* but never recover *why* from code alone).
- **Contradicts the naive reading of the code** — the highest-value class. A function whose name lies; a "temporary" workaround that's load-bearing; a cache that's actually the source of truth; an ORM model that diverges from the live schema. Flag these first.

### Test 2 — Behavior-change
*If the agent didn't know this, would it write materially wrong or unsafe code?*
- **YES → high-value, prefer lean.** (Editing a Core business rule it didn't know about; touching a high-risk cascade zone; relying on an ORM field that doesn't exist in the live DB.)
- **NO → deep at most.** (Nice-to-know context that doesn't change what the agent would write.)

A finding that is both **non-inferable (Test 1)** and **behavior-changing (Test 2)** is a lean-tier candidate. Non-inferable but not behavior-changing → deep. Inferable → drop from lean regardless of Test 2.

### Test 3 — Root-cause dedup
Collapse N findings that share one underlying cause into one. (Five "missing null check" warnings across one module → one finding citing the module + the pattern.) Keep the most specific `file:line` as the anchor; fold the rest into the reason. Prevents the lean tier from filling with surface repetitions of a single root issue.

## Decision procedure (per finding)
```
if INFERABLE (Test 1):              tier = drop-from-lean; non_obvious = false
else:                               non_obvious = true
    dedup against existing findings (Test 3)
    if behavior-changing (Test 2):  tier = lean (subject to budget below)
    else:                           tier = deep
```

## Lean-tier selection (the ~100-line budget, DP-2)
The lean tier is a *ranked shortlist*, not "everything non-obvious." After tagging, rank lean-candidates by: (1) behavior-change severity (Core > Supporting; high-risk cascade > isolated), (2) "contradicts naive reading" findings first, (3) breadth of impact (cross-component > single-file). Fill the root `AGENTS.md` budget (~100 lines, soft; `--max-lines` overridable) top-down; everything that doesn't make the cut stays in the deep tier with full detail. Per-component `AGENTS.md` files get the same treatment scoped to that component (nearest-file-wins).

**Behavioral / relational facts rank with "contradicts naive reading."** The under-captured kinds from `extraction.md` Q10–Q12 — **key invariants** (value-semantics/immutability, never-empty/ordering, the core data structure's load-bearing property, lifecycle ordering), **boundary / layer rules** (layering direction & what must-not-cross, required traffic chains, error-propagation conventions, module-isolation), and the **system startup/boot sequence** — are non-inferable cross-file/relational facts whose absence makes an agent write materially wrong code (Test 1 + Test 2 both pass). When non-obvious and load-bearing they are **first-class lean candidates**, ranked alongside (2) above — not deprioritized as "ordinary BRs/WFs." (R9 still governs: an obvious or per-feature one stays deep.)

## Worked examples
| Finding | Verdict | Tier | Reason |
|---------|---------|------|--------|
| "`OrdersController` exposes REST CRUD for orders" | inferable | drop-from-lean | standard naming + framework convention |
| "`process()` actually *reverses* the transaction on retry" | non-obvious, behavior-changing | **lean** | contradicts the naive reading; editing it blind breaks retries |
| "Invoices over ₪10k require dual approval (BR-billing:003, Core)" | non-obvious, behavior-changing | **lean** | domain rule, not in code structure; Core criticality |
| "ORM `User.nickname` has no column in the live DB" | non-obvious, behavior-changing | **lean** | runtime/DB drift; code that reads it will fail |
| "Auth uses bcrypt with cost factor 12" | non-obvious, low behavior-change | deep | not derivable from names, but rarely changes what an agent writes |
| "`utils/` holds 14 helper functions" | inferable | drop-from-lean | listable from the directory |
| 6× "TODO: handle timeout" across `billing/` | dedup → 1 | deep | one root pattern, not six findings |

## Output annotation
Write each finding back with:
```
{id} | {claim} | non_obvious: {true|false} | reason: {one line} | tier: {lean|deep|drop-from-lean} | {file:line} | {certainty}
```
`generation.md` reads `tier` to place content; `verification.md` checks the `file:line` of everything that survives. The Filter never edits the underlying analysis in `.ai/docs/components/*.md` — that deep record stays complete; the Filter only governs what is *promoted* to the lean tier.
