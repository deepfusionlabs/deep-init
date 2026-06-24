<!--
 DeepInit provenance (R3)
 stage: EMIT (deep component doc)
 component: helpers
 run_id: run-2026-06-13-kemal-e2e
 inputs: extraction(helpers) · src/kemal/helpers/{helpers,macros,templates,exceptions,exception_page,utils}.cr @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
-->
# helpers

**Role.** View/response helper layer baked into global scope + shared utilities + the exception hierarchy + ECR templating.

**Paths.** `src/kemal/helpers/helpers.cr` · `macros.cr` · `templates.cr` · `exceptions.cr` · `exception_page.cr` · `utils.cr`

## Global helpers
- `helpers.cr` defines GLOBAL top-level helpers (not under `Kemal::`): `public_folder`, `logging`, `serve_static` (Bool/Hash overloads), `headers`, `send_file`, `gzip`, `static_headers` — plus DEPRECATED `add_handler`/`log`/`logger` (`helpers.cr:18,37,81`). `gzip(status)` installs `HTTP::CompressHandler` via `use` (`helpers.cr:284-286`). — `src/kemal/helpers/helpers.cr:18`
- `send_file` (`helpers.cr:137-179`) is the response-streaming workhorse: sets `X-Content-Type-Options nosniff` + `Accept-Ranges bytes`, honors a `Range` header via `multipart` (`helpers.cr:206-248`, single 206 partial + `multipart/byteranges`), and gzip/deflate-compresses only when `serve_static['gzip']==true`, filesize > 860, the extension is a zip-type, and the client `Accept-Encoding` allows it (`helpers.cr:161-176`). The byte-slice overload writes data directly. — `src/kemal/helpers/helpers.cr:137`

## Templating & rendering macros
- `macros.cr` provides the ECR templating surface: `content_for`/`yield_content` (a `CONTENT_FOR_BLOCKS` global hash keyed by id), `render(filename[,layout])` (`ECR.embed`/`render`), `halt` (overloaded — closes the response and `next`-es out of the route block), and `add_context_storage_type` which PUSHes a type into `HTTP::Server::Context::STORE_MAPPINGS` at compile time (`macros.cr:126-128`). — `src/kemal/helpers/macros.cr:126`
- `templates.cr` provides `render_404` (a static HTML page) and `render_500(context, exception, verbosity)` which renders `Kemal::ExceptionPage` (dev, full trace) vs `ExceptionPage.for_production_exception` (terse) based on verbosity (`templates.cr:24-36`); `exception_page.cr` subclasses the `exception_page` shard and supplies Kemal branding. — `src/kemal/helpers/templates.cr:24`

## Exception hierarchy & utils
- `Kemal::Exceptions` (`exceptions.cr`) defines `InvalidPathStartException` / `RouteNotFound` / `CustomException` / `PayloadTooLarge` — all `< Exception`; `CustomException` carries the context and a default `'Rendered error with {status}'` message (`exceptions.cr:16-18`). — `src/kemal/helpers/exceptions.cr:16`
- **BR-core:003 — leading-slash precondition (boundary rule).** Every route/ws/sse/filter path MUST start with `/`; the DSL and Router validate via `Utils.path_starts_with_slash?` and raise `Kemal::Exceptions::InvalidPathStartException` otherwise — enforced at registration time, not request time. — `src/kemal/helpers/utils.cr:5`
- `Utils` (`utils.cr`) holds `ZIP_TYPES` (the compressible extension allow-list) + `path_starts_with_slash?` (the leading-slash rule used by every route/ws/sse DSL) + `zip_types(path)`. — `src/kemal/helpers/utils.cr:1`

## Cross-component edges
- helpers → handlers: `gzip` installs `HTTP::CompressHandler` via `use`; the exception classes are rescued by `ExceptionHandler`.
- helpers → ext: `add_context_storage_type` pushes into `STORE_MAPPINGS` (defined in `ext/context.cr`) — a compile-time contract between helpers and ext.
- helpers ← router/core DSL: `path_starts_with_slash?` is the shared leading-slash gate.
