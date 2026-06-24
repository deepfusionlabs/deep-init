<!-- DEEPINIT:START (managed — regenerated on each run; edit OUTSIDE these markers) -->
<!--
 DeepInit provenance (R3)
 stage: REDACT → EMIT → ADR (lean root)
 run_id: run-2026-06-13-kemal-e2e
 inputs: filter.md(lean/deep facts) · adr.md · global-rules.md · src/** @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747 (kemalcr/kemal)
 note: content inside these markers is DeepInit-owned and regenerated; edit outside them.
-->
# kemal — Agent Context

Kemal is a lean, Sinatra-style HTTP web framework for the Crystal language: a global-scope DSL (`get "/" {... }`, `ws`, `sse`, `before_all`, `use`, `mount`) layered over a fixed `HTTP::Handler` middleware chain that a single process-wide `Config` singleton assembles and owns.

## Architecture
A composable `HTTP::Handler` middleware pipeline driven by a Sinatra-style global DSL over a process-global `Config` singleton. The whole `src/kemal/` tree is loaded by three glob `require`s in `src/kemal.cr`; files reference siblings by fully-qualified constants, not per-file imports. Components map to `.ai/docs/components/`.

## Components (7)
- **core** — entry point + global run/stop lifecycle + the `Config` singleton that assembles the ordered handler chain + the top-level DSL + CLI/SSL. → `.ai/docs/components/core.md`
- **handlers** — the `HTTP::Handler` middleware links (init, exception, head, override-method, path, static-file, filter) + the base handler with only/exclude matching. → `.ai/docs/components/handlers.md`
- **router** — route storage/matching/dispatch: the terminal `RouteHandler` + LRU route cache, the modular `Router` DSL, and param parsing with body-size guards. → `.ai/docs/components/router.md`
- **websocket** — real-time transports: `WebSocketHandler` (Origin allow-list), the WS route wrapper, and Server-Sent Events. → `.ai/docs/components/websocket.md`
- **helpers** — global view/response helpers, ECR templating macros, the exception hierarchy, and path/zip utilities. → `.ai/docs/components/helpers.md`
- **logging** — pluggable request-logging abstraction (deprecated in favor of stdlib `Log`); the default `RequestLogHandler` + legacy/no-op loggers. → `.ai/docs/components/logging.md`
- **ext** — stdlib monkey-patches (NOT under `Kemal::`): reopens `HTTP::Server::Context` (params/redirect/route lookup + typed `@store`) and `HTTP::Server::Response`. → `.ai/docs/components/ext.md`

## Critical to know (non-obvious, load-bearing)
*Ranked: contradicts-naive-reading first, then key invariants / boundary rules / the boot sequence, then Core behavioral facts.*

- Exception handlers are matched by ORDER OF DECLARATION, not nearest-inheritance — the first *registered* compatible handler wins (`ex.class <= expected_exception`). Documented in-code as intentional; naive readers expect most-specific-wins. — `src/kemal/exception_handler.cr:24` [BR-handlers:003]
- The default middleware chain is assembled in a FIXED, position-counted order (NOT registration order); the two terminal handlers `WebSocketHandler::INSTANCE` then `RouteHandler::INSTANCE` are ALWAYS appended last, and custom (`use`) handlers always land between the built-ins and those terminal handlers. — `src/kemal/config.cr:140` [BR-core:001]
- There is NO per-application isolation: `Config::INSTANCE` plus the class-constant arrays HANDLERS/CUSTOM_HANDLERS/FILTER_HANDLERS/ERROR_HANDLERS/EXCEPTION_HANDLERS are process-global mutable state shared by the global DSL, every Router, and every handler; `Config.clear` is the ONLY reset seam (tests/sub-apps share one registry). — `src/kemal/config.cr:11` [BR-core:002]
- Filter order is invariant `before_all → before_x → X → after_x → after_all`, and global filters live in `@global_filters` and NEVER enter the radix `@tree`, so a path lookup cannot match them twice — duplicate `before_all`/`after_all` execution is structurally impossible (the #757 fix this commit carries). — `src/kemal/filter_handler.cr:40` [BR-handlers:002]
- WebSocket upgrades are rejected 403 unless the request Origin (normalized to `scheme://host[:port]`, default-port-stripped, lowercased; literal `null` supported) matches a non-empty `websocket_allowed_origins`; an EMPTY allow-list disables the check (allow-all). This is the cross-site-WebSocket-hijacking boundary. — `src/kemal/websocket_handler.cr:45` [BR-websocket:001]
- Request body size is capped TWO independent ways so a missing/lying `Content-Length` can't bypass the limit: `validate_content_length!` rejects an oversized declared length, and `LimitedBodyIO`/`read_body_with_limit` enforce `max_request_body_size` while streaming, raising `PayloadTooLarge` → 413. — `src/kemal/param_parser.cr:227` [BR-router:002]
- The `HTTP::Handler` chain contract: a handler does work then calls `call_next(context)` to advance; a handler that returns WITHOUT `call_next` terminates the chain for that request (e.g. WebSocketHandler on a 403 reject, PathHandler on a prefix miss). `RouteHandler::INSTANCE` is the terminal link and raises `RouteNotFound` when no route matches. — `src/kemal/handler.cr:35` [BR-handlers:001]
- `RouteHandler#process_request` always cleans up per-request multipart temp files in an `ensure` block (`context.params.cleanup_temporary_files`), so a raising route handler never leaks `FileUpload` tempfiles; `FileUpload`'s constructor also cleans up + re-raises on a copy failure. — `src/kemal/route_handler.cr:173` [BR-router:001]
- System boot is one ordered call-chain in `Kemal.run`: `CLI.new(args)` parses ARGV into Config (aborts on missing SSL key/cert) → `Kemal.config` singleton → `config.setup` assembles the chain → (non-test) `setup_404` + `setup_trap_signal` → `server = HTTP::Server.new(config.handlers)` → `running=true` → `yield config` → early-return if the block called `Kemal.stop` → `bind_tls`/`bind_tcp` → `display_startup_message` → `server.listen` (blocks; skipped when `env==test`). — `src/kemal.cr:33` [WF-core:001]
- `config.setup` is idempotent-guarded (`unless @default_handlers_setup && @router_included`), so repeated `Kemal.run`/`mount` calls do not double-insert the default chain. — `src/kemal/config.cr:141` [BR-core:004]

## Where to look
- Component detail → `.ai/docs/components/{name}.md`
- Why decisions were made → `.ai/docs/decisions.md`
- Known issues (drift, contradictions, coupling, unenforced rules) → `.ai/docs/issues.md` *(0 verified fires; 9 named suppressions)*
- Run manifest + hashes → `.ai/docs/manifest.json`
- Navigational dashboard → `.ai/dashboard.html` · Machine-readable findings → `.ai/deepinit.sarif`
<!-- DEEPINIT:END -->
