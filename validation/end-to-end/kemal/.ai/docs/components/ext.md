<!--
 DeepInit provenance (R3)
 stage: EMIT (deep component doc)
 component: ext
 run_id: run-2026-06-13-kemal-e2e
 inputs: extraction(ext) · src/kemal/ext/{context,response}.cr @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
-->
# ext

**Role.** Standard-library monkey-patches (Crystal open-class extensions, **NOT under the `Kemal::` module**). Loaded by the separate `require "./kemal/ext/*"` glob (`kemal.cr:6`).

**Paths.** `src/kemal/ext/context.cr` · `src/kemal/ext/response.cr`

## Context extension (the request lifecycle seam)
- `ext/context.cr` REOPENS `HTTP::Server::Context` (stdlib, NOT under `Kemal::`) to bolt Kemal's request lifecycle onto the stdlib context: `params` (lazily builds `ParamParser` from the cached ws-or-http route lookup), `route`/`websocket`/`route_lookup`/`ws_route_lookup` (cached via `@cached_route_lookup`/`@cached_ws_route_lookup`, established in a `macro finished` block, `context.cr:11-16`), `route_found?`/`ws_route_found?`, the typed `@store` session map with `get`/`set`/`get?`, `status` (chainable), and `json`/`html`/`xml`/`text` response writers. — `src/kemal/ext/context.cr:11`
- The `@store` session map type is the compile-time Union of `STORE_MAPPINGS = [Nil, String, Int32, Int64, Float64, Bool]` (`context.cr:9`); `add_context_storage_type` (`helpers/macros.cr:126`) extends this list — store typing is a cross-file compile-time contract between ext and helpers. — `src/kemal/ext/context.cr:9`
- `invalidate_route_cache` (`context.cr:52-60`) clears the cached route lookup AND, if params were already built, re-resolves the route and pushes the new url params into the existing `ParamParser` via `update_url_params` — the seam `OverrideMethodHandler` relies on after rewriting `request.method`. — `src/kemal/ext/context.cr:52`
- `redirect` (`context.cr:29-34`) sets `Location` + status (default 302) and CLOSES the response by default (`close: true`) — the source of the BR-handlers:004 closed-response convention. — `src/kemal/ext/context.cr:29`

## Response extension (legacy, compiled out on modern Crystal)
- `ext/response.cr` REOPENS `HTTP::Server::Response::Output` but is GUARDED to no-op on Crystal ≥1.3.0 via `{{ skip_file if compare_versions(...) }}` (`response.cr:3`) — a legacy Content-Length fix (issue #627) compiled out on modern Crystal; effectively dead on any current toolchain. This is documented dead code, not drift (see `.ai/docs/issues.md` IF-4/IF-10 suppressions). — `src/kemal/ext/response.cr:3`

## Cross-component edges
- ext ← router/handlers/websocket: every handler reads `context.params`/`context.route_found?`/`context.ws_route_found?` — this component is the lifecycle substrate they all share.
- ext ↔ helpers: `STORE_MAPPINGS` is defined here and extended by `helpers/macros.cr add_context_storage_type` (compile-time union contract).
- ext ← handlers: `OverrideMethodHandler` depends on `invalidate_route_cache` after rewriting `request.method`.
