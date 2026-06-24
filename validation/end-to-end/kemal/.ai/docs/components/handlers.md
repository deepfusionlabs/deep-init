<!--
 DeepInit provenance (R3)
 stage: EMIT (deep component doc)
 component: handlers
 run_id: run-2026-06-13-kemal-e2e
 inputs: extraction(handlers) · src/kemal/{handler,init_handler,exception_handler,head_request_handler,override_method_handler,path_handler,static_file_handler,filter_handler,file_upload}.cr @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
-->
# handlers

**Role.** The `HTTP::Handler` middleware chain — the pipeline links assembled by `config.cr:140-154`. Each concrete middleware `include HTTP::Handler` and implements `call`/`call_next`.

**Paths.** `src/kemal/handler.cr` · `init_handler.cr` · `exception_handler.cr` · `head_request_handler.cr` · `override_method_handler.cr` · `path_handler.cr` · `static_file_handler.cr` · `filter_handler.cr` · `file_upload.cr`

## The chain contract
- **BR-handlers:001 — every middleware includes `HTTP::Handler`.** The contract is: do work, then call `call_next(context)` to advance; a handler that returns WITHOUT `call_next` terminates the chain for that request (WebSocketHandler on a 403 reject; PathHandler on a prefix miss; StaticFileHandler serves-or-`call_next`). `RouteHandler::INSTANCE` is the terminal link and raises `RouteNotFound` when no route matches. — `src/kemal/handler.cr:35`
- `HandlerInterface` (`handler.cr:11`) adds the only/exclude path-matching macros backed by per-class `@@only_routes_tree`/`@@exclude_routes_tree` Radix trees (`handler.cr:14-17`); `Kemal::Handler` is the base class that includes it (`handler.cr:91-93`). `only_match?`/`exclude_match?` are NOT applied automatically — `handler.cr:44` notes the custom handler must call them. — `src/kemal/handler.cr:11`

## Concrete middlewares
- **InitHandler** (`init_handler.cr`) seeds every response: `X-Powered-By: Kemal` (only if `Kemal.config.powered_by_header?`), defaults Content-Type to `text/html` if unset, stamps a `Date` header; inserted FIRST in the chain. — `src/kemal/init_handler.cr:11`
- **ExceptionHandler** (`exception_handler.cr`) is the central error funnel: `call_next` wrapped in rescue clauses ordered `RouteNotFound → 404`, `CustomException → its status_code`, `PayloadTooLarge → 413` (or custom 413 handler), then a generic `rescue ex: Exception`, logs (`Log.error`, `exception_handler.cr:30`), then a custom 500 handler or `render_500` (verbosity off in production). — `src/kemal/exception_handler.cr:7`
 - **BR-handlers:003 — match by declaration order (NOT inheritance).** The generic fallback matches a registered exception handler by ORDER OF DECLARATION using `ex.class <= expected_exception`, deliberately NOT by nearest-inheritance: the first registered compatible handler wins. Documented in-code as intentional (`exception_handler.cr:22-23`). — `src/kemal/exception_handler.cr:24`
 - **BR-handlers:004 — never write to a closed response.** Every render helper short-circuits with `return if context.response.closed?` (`exception_handler.cr:47,56,66`), and `redirect` closes the response by default. Convention: once closed, downstream handlers must not write. — `src/kemal/exception_handler.cr:47`
- **HeadRequestHandler** swaps the response output for a private `NullIO` that COUNTS bytes without sending a body on HEAD requests, and on close sets Content-Length from the counted bytes (respecting RFC 7230: 304/204/1xx get no content-length). — `src/kemal/head_request_handler.cr:36`
- **OverrideMethodHandler** is OPT-IN (not in the default chain; doc at `override_method_handler.cr:5-8`). On a POST whose body `_method ∈ {PUT,PATCH,DELETE}` it rewrites `request.method` and calls `context.invalidate_route_cache`; it CONSUMES `params.body` (documented caveat). — `src/kemal/override_method_handler.cr:19`
- **PathHandler** wraps another handler to run only for a path prefix; `matches_prefix?` treats `/` or `''` as match-all, exact match, or prefix-followed-by-`/` — so `/api` matches `/api` and `/api/...` but NOT `/apiv2` (`path_handler.cr:36-44`). It rewires `@handler.next = self.next` before delegating (`path_handler.cr:25`). — `src/kemal/path_handler.cr:36`
- **StaticFileHandler** subclasses `HTTP::StaticFileHandler` and FORKS on Crystal version: Crystal ≥1.17.0 overrides `directory_index` + `serve_file` (deliberately opts OUT of content-range serving, `static_file_handler.cr:29`); older Crystal carries a full hand-rolled `call` with NUL-byte rejection (`static_file_handler.cr:55-58`), redirect normalization, dir_index/dir_listing, 304 caching. — `src/kemal/static_file_handler.cr:3`
- **FilterHandler** dispatches before/after filters (see `router` doc + BR-handlers:002); global filters kept in `@global_filters`, never in the radix `@tree` (#757 fix); `@exact_filters` is an O(1) hash cache over the tree (`filter_handler.cr:11`). `FilterHandler.call` (`filter_handler.cr:41-58`) raises `CustomException` when, after the before filters, an error handler is registered for the current status_code (filters can short-circuit into the error path); on no route found it still runs `before_all` (if a 404 handler exists) then `call_next`. — `src/kemal/filter_handler.cr:11`
 - **BR-handlers:002 — filter order + exactly-once.** `FilterHandler` enforces `before_all → before_x → X → after_x → after_all` (`filter_handler.cr:40`); global filters live in `@global_filters` and NEVER enter the radix `@tree`, so a path lookup cannot match them twice — duplicate `before_all`/`after_all` execution is structurally impossible (the #757 fix this commit b73de3d carries). — `src/kemal/filter_handler.cr:40`
- **FileUpload** streams an upload to a `File.tempfile` in its constructor; on a copy error it calls `cleanup` (close + delete) then re-raises (`file_upload.cr:13-19`) — temp files are not leaked on failure. — `src/kemal/file_upload.cr:13`

## Cross-component edges
- handlers ← core: assembled in fixed order by `config.setup` (BR-core:001).
- ExceptionHandler ↔ router/helpers: rescues `RouteNotFound`/`CustomException`/`PayloadTooLarge` (defined in `helpers/exceptions.cr`); renders via `templates.cr render_500`.
- FilterHandler ← router: `Router#register_filters` re-adds `FilterHandler::INSTANCE` defensively after `Config.clear`.
