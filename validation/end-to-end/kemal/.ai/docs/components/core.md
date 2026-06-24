<!--
 DeepInit provenance (R3)
 stage: EMIT (deep component doc)
 component: core
 run_id: run-2026-06-13-kemal-e2e
 inputs: extraction(core) · src/kemal.cr, src/kemal/{dsl,config,cli,ssl}.cr @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
-->
# core

**Role.** Framework entry point + global run/stop lifecycle + the user-facing DSL baked into top-level scope. Owns the `Config` singleton that holds every option and assembles the ordered middleware chain.

**Paths.** `src/kemal.cr` · `src/kemal/dsl.cr` · `src/kemal/config.cr` · `src/kemal/cli.cr` · `src/kemal/ssl.cr`

## Entry point & boot sequence
- `Kemal.run` is overloaded 4 ways (`kemal.cr:13/18/23/33`); the real body is at `src/kemal.cr:33` — `def self.run(port, args = ARGV, trap_signal = true, &)`.
- **WF-core:001 — system boot is one ordered call-chain** (background process). `Kemal.run`: (1) `Kemal::CLI.new(args)` parses ARGV into Config + configures SSL [`kemal.cr:34`, `cli.cr:6-15`]; (2) `config = Kemal.config` (the singleton); (3) `config.setup` assembles the ordered HANDLERS chain [`config.cr:140`]; (4) optional port override; (5) non-test only: `setup_404` registers a default 404 handler unless present + `setup_trap_signal` installs `Process.on_terminate → Kemal.stop → exit` [`kemal.cr:41-43,95-109`]; (6) `server = config.server ||= HTTP::Server.new(config.handlers)`; (7) `config.running = true` then `yield config` to the user block; (8) early return if the block called `Kemal.stop`; (9) `bind_tls`/`bind_tcp`; (10) `display_startup_message`; (11) `server.listen` (blocks) unless `env == test`. — `src/kemal.cr:33`

## Config singleton (process-global state)
- **BR-core:002 — no per-application isolation.** `Config::INSTANCE` (`config.cr:11`) plus the class-level mutable constants HANDLERS/CUSTOM_HANDLERS/FILTER_HANDLERS/ERROR_HANDLERS/EXCEPTION_HANDLERS (`config.cr:12-16`) are process-global mutable state that the global-scope DSL, every Router, and every handler register into. `Kemal.config` returns that one instance (`config.cr:209`). Intentional Sinatra-style design, but tests/sub-apps share one registry. — `src/kemal/config.cr:11`
- **BR-core:001 — fixed chain assembly order.** `config.setup` (`config.cr:140-154`) builds the chain in fixed, position-counted order via `@handler_position`: InitHandler → [RequestLogHandler if `@logging`] → HeadRequestHandler → [ExceptionHandler if `@always_rescue`] → [StaticFileHandler if `serve_static` is a Hash] → custom (`use`) handlers → filter handlers → `WebSocketHandler::INSTANCE` → `RouteHandler::INSTANCE`. The two terminal handlers are always appended LAST (`config.cr:151-152`); custom handlers always sit between the built-ins and the terminal Route/WS handlers. — `src/kemal/config.cr:140`
- **BR-core:004 — idempotent setup.** Guarded by `unless @default_handlers_setup && @router_included`, so repeated `Kemal.run`/`mount` does not double-insert the default chain; `@handler_position` monotonically advances within a single setup to preserve insertion order. — `src/kemal/config.cr:141`
- **`Config.clear`** (`config.cr:80-94`) resets all flags AND clears the 5 shared handler collections — the test-reset / re-init seam; `handlers=` (`config.cr:100-103`) calls `clear` then replaces. — `src/kemal/config.cr:80`
- **VERSION** (`config.cr:2`) is resolved at COMPILE time by shelling out `shards version` — a build-time macro, not a runtime read. — `src/kemal/config.cr:2`
- Default legacy logger precedence: `setup_log_handler` uses `@logger || RequestLogHandler.new` (`config.cr:164`), so a deprecated `BaseLogHandler` subclass still takes precedence when set. — `src/kemal/config.cr:164`

## The DSL (global top-level scope)
- `dsl.cr` is baked into GLOBAL top-level scope (not under `Kemal::`). `get/post/put/patch/delete/options` are macro-generated from HTTP_METHODS (`dsl.cr:12,28-33`); each raises `InvalidPathStartException` unless the path starts with `/` and delegates to `RouteHandler::INSTANCE.add_route`. `before_*/after_*` are macro-generated over FILTER_METHODS (incl. `all`) × [before, after] (`dsl.cr:123-135`). — `src/kemal/dsl.cr:28`
- `use` is overloaded (`dsl.cr:143-181`): plain handler → `config.add_handler`; with position; with a path prefix → wraps in `Kemal::PathHandler.new(path, handler)`; with a path + Enumerable of handlers. `mount(router)` calls `register_routes`; `mount(path, router)` prefixes. — `src/kemal/dsl.cr:143`
- `sse` routes are GET routes whose handler wraps `EventStream.serve` (`dsl.cr:63-68`) — SSE is not a separate transport at the routing layer; it reuses `RouteHandler`. — `src/kemal/dsl.cr:63`

## CLI & SSL
- `CLI` (`cli.cr`) parses ARGV via `OptionParser` into Config (`-b/--bind`, `-p/--port`, `-s/--ssl`, `--ssl-key-file`, `--ssl-cert-file`, `-h`); `--help` calls `exit 0`; `@config.extra_options.try &.call(opts)` lets apps inject options (`cli.cr:38`). `configure_ssl` ABORTS the process if `--ssl` is set but key/cert is missing (`cli.cr:45-46`). — `src/kemal/cli.cr:42`
- `SSL` (`ssl.cr`) is a thin wrapper over `OpenSSL::SSL::Context::Server`; `key_file=`/`cert_file=` set `private_key`/`certificate_chain`. — `src/kemal/ssl.cr:1`

## Cross-component edges
- core → handlers/router/websocket: `config.setup` appends `WebSocketHandler::INSTANCE` and `RouteHandler::INSTANCE` (constant references resolved after the umbrella glob load).
- DSL `get/ws/sse` → router/websocket: delegate to the `RouteHandler`/`WebSocketHandler` INSTANCE singletons.
- DSL `use` → handlers: wraps in `PathHandler` for the path-prefix form.

## Design rationale
The Sinatra-style global DSL + process singleton is the deliberate ergonomic choice — `get "/" { }` at top level requires global mutable registries. See `.ai/docs/decisions.md` (ADR-0001, ADR-0002).
