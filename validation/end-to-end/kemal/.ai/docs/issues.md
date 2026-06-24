<!--
 DeepInit provenance (R3)
 stage: REDACT → EMIT (deep issue ledger — REGENERATED, not an owned-region merge)
 run_id: run-2026-06-13-kemal-e2e
 inputs: issues(verified)=[] · suppressions[9] · components[7] · src/** @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
 report-only · 100% local · flags-likely-not-proven · redaction passed (no secrets/PII — OSS framework, no data samples)
-->
# Issue ledger — kemal

**Summary:** 0 verified issues / 9 named suppressions. DeepInit declines to fabricate ungroundable fires; every candidate it considered and chose NOT to file is recorded below with the predicate-FALSE mechanism that suppressed it (degrade-don't-false-flag, R1). This is the expected posture for a mature, intentionally-designed OSS HTTP framework.

## 1. Verified issues

| ISS-id | Family | Claim | Provenance | Severity | Certainty | Verified | Lifecycle |
|--------|--------|-------|------------|----------|-----------|----------|-----------|
| — | — | *(none)* | — | — | — | — | — |

No issue survived verification this run. The SARIF `results[]` is correspondingly empty (a valid run).

## 2. Named suppressions (the candidates considered and why they did NOT fire)

Each row names a real structural candidate and the gate clause that holds it below the precision-first bar — never silent.

### IF-8 — circular component dependency
**Verdict: structurally inapplicable as an IMPORT cycle (permitted+textual model).**
Crystal/kemal uses the permitted+textual model: the ONLY `require` statements are three glob requires in the umbrella `src/kemal.cr` (`require "./kemal/*"`, `"./kemal/ext/*"`, `"./kemal/helpers/*"`). No file imports a sibling; every file reopens `module Kemal` and references siblings by fully-qualified constants (e.g. `Kemal::RouteHandler::INSTANCE`) resolved after the single glob load. There are therefore NO per-file import edges to form an SCC. Mutual cross-references DO exist between components (config↔handlers↔router↔websocket via constant references), but the spec's IF-8 detector keys on the structural import graph; a component-SCC computed from constant-reference would be a granularity artifact of the glob-load model, not a compile-time import cycle (cf. the nginx permitted+textual datapoint). **Suppress: no import-edge substrate to fire on.**

### IF-3a — silent cross-component coupling (serve_static magic-string keys)
**Verdict: an EXPLICIT interface mediates the resource → below the bar.**
Candidate: the string keys `'dir_index'`/`'dir_listing'`/`'gzip'` are written as the default hash in core (`config.cr:43`) and read by literal key in handlers (`static_file_handler.cr:11,21,84,95`) and helpers (`helpers.cr:161`) with no shared constant. SUPPRESS: all reads go through the `Config` singleton's public `serve_static` accessor (`Kemal.config.serve_static`), and the keys are the documented public option surface (`helpers.cr:93-97`). The IF-3a gate requires a named resource read/written by ≥2 components WITH NO EXPLICIT INTERFACE; here the Config accessor IS the interface. Residual risk (a key typo silently disabling a feature) is real but LOW.

### IF-3a — silent cross-component coupling (Config global mutable HANDLERS arrays)
**Verdict: intentional, documented singleton design + mediated access → below the bar.**
Candidate: HANDLERS/CUSTOM_HANDLERS/FILTER_HANDLERS/ERROR_HANDLERS/EXCEPTION_HANDLERS are class constants on Config, mutated by core (`config.cr`) and Router (`router.cr:271` reads `Kemal::Config::FILTER_HANDLERS` directly). SUPPRESS: this is the intentional, documented singleton design (`config.cr:4-9` "It's a singleton") and access is mediated through Config's public methods (`add_handler`/`add_filter_handler`/`handlers`); the one direct constant read in `router.cr:271` is a defensive idempotency check, not a silent coupling. The coupling is the architecture's central, named, documented contract — captured as **BR-core:002** — not a hidden change-one-break-the-other resource.

### IF-3a — silent cross-component coupling (STORE_MAPPINGS)
**Verdict: a compile-time macro contract / documented extension API → below the bar.**
Candidate: `HTTP::Server::Context::STORE_MAPPINGS` is defined in ext (`context.cr:9`) and pushed to by helpers' `add_context_storage_type` macro (`macros.cr:126-128`). SUPPRESS: this is a COMPILE-TIME macro contract (the array is consumed by `macro finished` to build the StoreTypes union, `context.cr:11-12`), exposed deliberately as the documented extension API; it is a public, named extension seam, not a silent runtime resource coupling. Captured as a component fact + BR.

### IF-1 — business-rule violation / inconsistent enforcement
**Verdict: no rule to check inconsistency against → suppress (degrade-don't-false-flag).**
No documented Core/Supporting business rule is enforced on one path but absent on a sibling path to the same entity+operation. kemal is an HTTP framework, not a domain app with ownership/authorization rules over entities. The closest invariants (body-size cap, leading-slash precondition, response-closed guard) are each enforced uniformly across all reaching paths (the body-size cap is even double-guarded, BR-router:002). No guarded-vs-unguarded sibling contrast exists.

### IF-4 — intent/decision contradiction
**Verdict: dual-citation impossible (no decision side) → suppress.**
No ADR/decision-log in the repo, and no code observed contradicting a recorded rule, a name-that-lies, a stale workaround, or a load-bearing TODO/FIXME on a Core path (no TODO/FIXME/HACK markers found in `src/`). Deprecated APIs (`add_handler`/`log`/`logger`/`LogHandler`/`NullLogHandler`/`BaseLogHandler`) are correctly `@[Deprecated]`-annotated with the replacement named ("Use standard library `Log`" / "Use `use` instead") — that is honest documentation of intent, not a contradiction. The `ext/response.cr` legacy override is explicitly compiled out on Crystal ≥1.3 with an in-code rationale + issue link (#627) — documented dead code, not drift.

### IF-6 — divergent named allowed-value set
**Verdict: no non-empty symmetric difference under a shared name → suppress.**
No named literal value-set is defined under the same canonical name in ≥2 distinct components with conflicting membership. The named sets present are single-owner: `ZIP_TYPES` (`helpers/utils.cr:3`), `STORE_MAPPINGS` (`ext/context.cr:9`), `ALLOWED_METHODS`/`HTTP_METHODS`/`FILTER_METHODS`/`PARTS` (each in one file). The duplicated `elapsed_text` method (`request_log_handler.cr:13` and the deprecated `log_handler.cr:22`) is same-LOGIC duplication with IDENTICAL behavior, not a divergent named value-set — that is the deferred semantic-IF-6 (same-logic, no shared name), explicitly out of the deterministic slice's scope, and the copies do not diverge anyway.

### IF-7c — cross-boundary swallowed error
**Verdict: predicate-FALSE (re-raise + error-as-value) → suppress.**
No bare empty / comment-only error handler exists. The two rescue sites are both NON-empty and deliberate: `param_parser.cr:120` `rescue value` returns the original (unescaped) value (an error-as-value fallback, not a swallow), and `file_upload.cr:17-19` rescues, calls `cleanup`, then re-raises (`raise ex`) — propagation, the opposite of a swallow. Crystal has no Java-style checked exceptions; the central error funnel is `ExceptionHandler` which logs (`Log.error`, `exception_handler.cr:30`) and renders rather than discarding.

### IF-10 — statically-dead const-gated branch
**Verdict: no literal-const indirection feeding a runtime `if` → suppress (config-as-compile-flag).**
No module-level compile-time-literal constant is used as the WHOLE test of a conditional with a statically-dead arm. The conditionals in `src/` test runtime/instance state (`@logging`, `@always_rescue`, `@serve_static.is_a?(Hash)`, `config.powered_by_header?`, request methods/headers) or config values — none is a const-folded literal. The compile-time `{% if flag?(:without_openssl) %}` / `{% if compare_versions(Crystal::VERSION,...) %}` / `{{ skip_file if... }}` macros (`config.cr:18`, `static_file_handler.cr:3`, `ext/response.cr:3`, `helpers.cr:1`) are Crystal MACRO conditionals resolved by the compiler against build flags / toolchain version — config-as-compile-flag (the deliberate, intended build-variant mechanism), the analog of nginx's IF-10-muted-via-preprocessor datapoint, not a dead const-gated runtime branch.

## 3. Honesty note
This ledger is report-only and 100% local. Zero fires on a framework this mature is the expected, correct outcome — the suppressions above are the evidence DeepInit *looked* and grounded every non-fire, rather than the absence of analysis. Several couplings that a naive scanner would flag (the global `Config` singleton, the `serve_static` magic keys, `STORE_MAPPINGS`) are instead captured as first-class **context facts / BRs** in the component docs, where they belong.
