<!--
 DeepInit provenance (R3)
 stage: ADR (decisions + knowledge log — REGENERATED)
 run_id: run-2026-06-13-kemal-e2e
 inputs: extraction Design Rationale (all 7 components) · in-code rationale comments · src/** @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
-->
# Decisions & Knowledge Log — kemal

The *why* behind kemal's structure, inferred from intentional patterns + in-code rationale (no ADR folder exists in the repo, so each ADR below is `inferred` and tagged with its certainty + grounding evidence). Speculative rationale is parked in Open Questions, not asserted as an ADR.

## ADR-0001: Process-global `Config` singleton + class-constant handler registries
- **Status:** accepted (inferred)
- **Date:** unknown — inferred
- **Context:** A Sinatra-style framework wants `get "/" {... }` to work at top-level global scope with no app object to thread through. That requires a single, globally-reachable place to register routes, filters, handlers, and options.
- **Decision:** Make `Config` a process-wide singleton (`Config::INSTANCE`, `config.cr:11`) and hold the five handler collections (HANDLERS/CUSTOM_HANDLERS/FILTER_HANDLERS/ERROR_HANDLERS/EXCEPTION_HANDLERS) as class-level mutable constants the global DSL, every Router, and every handler mutate directly.
- **Why:** It is the minimum machinery that lets the global DSL register into one shared registry; the in-code comment at `config.cr:4-9` states "It's a singleton".
- **Evidence:** `src/kemal/config.cr:11` (INSTANCE), `config.cr:12-16` (the 5 constants), `config.cr:209` (`Kemal.config` returns the instance).
- **Consequences:** NO per-application isolation (BR-core:002): tests and sub-apps share one registry. `Config.clear` (`config.cr:80-94`) is the ONLY reset seam — hence the defensive `register_filters` re-registration in `router.cr:271`. This is the load-bearing tradeoff of the whole framework.
- **Certainty:** [HIGH]

## ADR-0002: A fixed-order `HTTP::Handler` middleware chain with terminal handlers appended last
- **Status:** accepted (inferred)
- **Date:** unknown — inferred
- **Context:** Requests must flow through a predictable pipeline (init → logging → head → exceptions → static → custom → filters → routing) regardless of the order users call `use`/`get`. Composing on Crystal's stdlib `HTTP::Handler` gives the chain for free.
- **Decision:** `config.setup` (`config.cr:140`) assembles the chain in a FIXED, position-counted order via `@handler_position`, and ALWAYS appends `WebSocketHandler::INSTANCE` then `RouteHandler::INSTANCE` last; custom (`use`) handlers always land between the built-ins and those terminal handlers.
- **Why:** The terminal Route/WS handlers must see a request only after every cross-cutting concern (logging, exceptions, static files, filters) has had its turn; a registration-order chain would let a user accidentally place routing before exception handling.
- **Evidence:** `src/kemal/config.cr:140` (setup), `config.cr:151-152` (terminal append), `handler.cr:35` (the `call_next` contract).
- **Consequences:** The pipeline is the load-bearing request contract (BR-core:001); custom handlers cannot run after routing. Idempotency-guarded (BR-core:004) so re-running `Kemal.run`/`mount` doesn't double-insert.
- **Certainty:** [HIGH]

## ADR-0003: Match exception handlers by declaration order, not nearest-inheritance
- **Status:** accepted (inferred)
- **Date:** unknown — inferred
- **Context:** When multiple registered handlers could rescue a raised exception (e.g. a base class and a subclass), the framework must pick one deterministically.
- **Decision:** The generic fallback iterates registered exception handlers in ORDER OF DECLARATION and takes the first whose expected type satisfies `ex.class <= expected_exception` (`exception_handler.cr:24`) — explicitly NOT nearest-inheritance.
- **Why:** Declaration order is predictable and user-controllable (register the most specific handler first); the in-code comment (`exception_handler.cr:22-23`) documents this as intentional: "Matches based on order of declaration rather than inheritance relationship".
- **Evidence:** `src/kemal/exception_handler.cr:24` + the comment at `:22-23`.
- **Consequences:** Contradicts the naive most-specific-wins expectation (BR-handlers:003); users who register a broad handler before a narrow one will have the broad one win. This is the most non-obvious behavior in the codebase.
- **Certainty:** [HIGH]

## ADR-0004: Keep global (`before_all`/`after_all`) filters out of the radix tree (the #757 fix)
- **Status:** accepted (inferred)
- **Date:** ~this commit (b73de3d carries the #757 fix) — inferred
- **Context:** Global filters and path-scoped filters were both stored in the radix `@tree`, so a path lookup could match a global filter a second time, running `before_all`/`after_all` twice.
- **Decision:** Store global filters in a separate `@global_filters` collection that NEVER enters the radix `@tree` (`filter_handler.cr:40`), making duplicate `before_all`/`after_all` execution structurally impossible while preserving the invariant order `before_all → before_x → X → after_x → after_all`.
- **Why:** Correctness — a filter that runs twice (e.g. an auth check, a counter) is a real bug; structural separation is more robust than a runtime dedup guard.
- **Evidence:** `src/kemal/filter_handler.cr:40` (the order comment + `@global_filters`); the commit this analysis pins (`b73de3d`) is the "Fix before_all filters running twice" (#757) fix.
- **Consequences:** BR-handlers:002 — the exactly-once guarantee is a structural property, not a defensive check. `@exact_filters` is an O(1) hash cache over the remaining tree.
- **Certainty:** [MEDIUM] — the structural mechanism is HIGH-certain from code; the attribution to #757 is inferred from the pinned-commit context.

## Knowledge Log

- **KL-architecture:001** | The whole `src/kemal/` tree loads via three glob `require`s in the umbrella `src/kemal.cr`; files reference siblings by fully-qualified constants, not per-file imports — so there is NO module-import graph (the permitted+textual model). | `src/kemal.cr:4-6` | [HIGH]
- **KL-preference:001** | The DSL (`dsl.cr`) and the view helpers (`helpers.cr`) are deliberately baked into GLOBAL top-level scope, NOT under `Kemal::` — the Sinatra ergonomic convention. | `src/kemal/dsl.cr:28`, `src/kemal/helpers/helpers.cr:18` | [HIGH]
- **KL-learning:001** | `VERSION` is resolved at COMPILE time by shelling out `shards version` (a macro), not read at runtime. | `src/kemal/config.cr:2` | [HIGH]
- **KL-architecture:002** | SSE is not a separate transport at the routing layer — `sse` routes are GET routes wrapping `EventStream.serve`, reusing `RouteHandler`. | `src/kemal/dsl.cr:63` | [HIGH]
- **KL-learning:002** | HEAD requests with no explicit HEAD route IMPLICITLY fall back to the GET handler, and the fallback is cached under the original HEAD key. | `src/kemal/route_handler.cr:144` | [HIGH]
- **KL-mistake:001** | `ext/response.cr` is documented dead code on modern Crystal — `{{ skip_file if compare_versions(...) }}` compiles it out on Crystal ≥1.3.0 (a legacy issue-#627 Content-Length fix). Don't rely on it. | `src/kemal/ext/response.cr:3` | [HIGH]
- **KL-preference:002** | The entire `logging` component (`BaseLogHandler`/`LogHandler`/`NullLogHandler`) is `@[Deprecated]` in favor of stdlib `Log`; only `RequestLogHandler` is the live default. | `src/kemal/base_log_handler.cr:3` | [HIGH]
- **KL-integration:001** | The `@store` session-map type union (`STORE_MAPPINGS`, `ext/context.cr:9`) is extended at compile time by `helpers/macros.cr add_context_storage_type` — a cross-file compile-time contract between `ext` and `helpers`. | `src/kemal/ext/context.cr:9` | [HIGH]

## Open Questions (not asserted as ADRs)
- The two-way expression of the WS path key (`radix_path('ws', path)` in `add_route` vs the literal `"/ws" + path` in `lookup_ws_route`) yields the same key but is written two different ways — likely incidental, not a deliberate decision; flagged as a readability note, not an ADR.
