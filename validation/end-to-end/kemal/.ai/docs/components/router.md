<!--
 DeepInit provenance (R3)
 stage: EMIT (deep component doc)
 component: router
 run_id: run-2026-06-13-kemal-e2e
 inputs: extraction(router) · src/kemal/{route_handler,router,route,param_parser}.cr @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
-->
# router

**Role.** Route storage, matching and dispatch. The terminal `RouteHandler` middleware plus a file-local LRU cache over a Radix tree; the modular `Router` DSL; the `Route` record; and param parsing with body-size guards.

**Paths.** `src/kemal/route_handler.cr` · `src/kemal/router.cr` · `src/kemal/route.cr` · `src/kemal/param_parser.cr`

## RouteHandler (terminal middleware)
- `RouteHandler` (`route_handler.cr:103`, `INSTANCE` singleton) is the TERMINAL middleware (appended last). `process_request` raises `RouteNotFound` unless `route_found?`, returns early if the response is already closed, calls the matched handler, raises `CustomException` if an error handler is registered for the resulting status_code (`route_handler.cr:166-167`), prints content, and in an `ensure` always runs `context.params.cleanup_temporary_files` (`route_handler.cr:173-174`). — `src/kemal/route_handler.cr:103`
- **BR-router:001 — terminal cleanup.** `RouteHandler#process_request` always cleans up per-request multipart temp files in an `ensure` block, so a route handler that raises does not leak `FileUpload` tempfiles; `FileUpload`'s constructor also cleans up + re-raises on a copy failure. — `src/kemal/route_handler.cr:173`
- Routes live in a `Radix::Tree(Route)` keyed `'/{METHOD}{path}'` (`route_handler.cr:177`). `lookup_route` caches into a file-local LRUCache and is Mutex-synchronized for concurrent fibers (`route_handler.cr:118-119,136`). **HEAD requests with no HEAD route IMPLICITLY fall back to the GET handler**, and the fallback is cached under the original HEAD key (`route_handler.cr:144-152`). — `src/kemal/route_handler.cr:133`
- **LRUCache** (`route_handler.cr:7-101`) is a deliberately minimal, file-local O(1) doubly-linked-list + Hash LRU; capacity = `Kemal.config.max_route_cache_size` (default 1024); intentionally not part of the public API. — `src/kemal/route_handler.cr:7`

## Router (modular DSL)
- `Router` (`router.cr`) is the modular DSL: it ACCUMULATES route/filter/ws/sse/sub-router definitions into arrays at definition time and only flushes them into the global `RouteHandler`/`WebSocketHandler`/`FilterHandler` INSTANCEs in `register_routes` (`router.cr:201-240`), invoked by `mount`; `namespace` builds a nested Router via `with sub_router yield` (`router.cr:168-172`). — `src/kemal/router.cr:201`
- `register_routes` recursively prefixes sub-routers (`router.cr:236-239`); `join_paths` normalizes slashes (`router.cr:323-329`); `validate_path!` enforces the leading-slash rule (`router.cr:331-335`); filters with path `'*'` apply to all collected route paths, otherwise to paths equal-to-or-prefixed-by the filter path (`router.cr:277-284`). — `src/kemal/router.cr:236`
- `register_filters` re-adds `FilterHandler::INSTANCE` to config if it was cleared between tests (`router.cr:271-273`) — defensive re-registration against `Config.clear`. — `src/kemal/router.cr:271`
- `Route` (`route.cr`) is a struct wrapping method/path/handler; the handler is normalized so a non-String block result becomes `''` (`route.cr:11-14`) — the same normalization `Router#add_route` applies (`router.cr:307-312`). — `src/kemal/route.cr:11`

## ParamParser & body-size guards
- `ParamParser` lazily parses url/query/body/json/files via a macro-generated memoized accessor per PART (`param_parser.cr:124-134`). — `src/kemal/param_parser.cr:124`
- **BR-router:002 — body-size double guard (security-adjacent).** Body size is guarded TWO ways: `validate_content_length!` against `max_request_body_size`, and `read_body_with_limit` / the private `LimitedBodyIO` cap while streaming (raising `PayloadTooLarge`) so a lying/absent `Content-Length` can't bypass the limit (`param_parser.cr:50-55,227-234`). Multipart fields use a separate `max_multipart_form_field_size` limit. — `src/kemal/param_parser.cr:227`
- `raw_body` is cached on first read and ONLY for url-encoded + JSON content types (`param_parser.cr:83-101`) so multiple handlers can read the body without consuming the IO; multipart fields use a separate `max_multipart_form_field_size` limit (`param_parser.cr:180,236-237`). — `src/kemal/param_parser.cr:83`
- Multipart file fields whose name ends with `'[]'` accumulate into `@all_files` (arrays); others into `@files` (`param_parser.cr:172-178`). — `src/kemal/param_parser.cr:172`

## Cross-component edges
- router → handlers: `ExceptionHandler` rescues the `CustomException`/`RouteNotFound`/`PayloadTooLarge` this component raises.
- router → ext: `process_request` reads `context.params` / `context.route_found?` (the lifecycle methods bolted on in `ext/context.cr`).
- router ← core/Router: `Router#register_routes` flushes into `RouteHandler::INSTANCE`.
