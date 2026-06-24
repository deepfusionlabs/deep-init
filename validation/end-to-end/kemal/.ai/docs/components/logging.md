<!--
 DeepInit provenance (R3)
 stage: EMIT (deep component doc)
 component: logging
 run_id: run-2026-06-13-kemal-e2e
 inputs: extraction(logging) · src/kemal/{base_log_handler,request_log_handler,log_handler,null_log_handler}.cr @ b73de3d8e6de
 date: 2026-06-13
 repo_sha: b73de3d8e6de97541866b6ecdc8c6ee1ef3eb747
-->
# logging

**Role.** Pluggable request-logging abstraction — **deprecated in favor of stdlib `Log`**. The default `RequestLogHandler` is the only non-deprecated implementation.

**Paths.** `src/kemal/base_log_handler.cr` · `request_log_handler.cr` · `log_handler.cr` · `null_log_handler.cr`

## The abstraction & the default
- `BaseLogHandler` (`base_log_handler.cr`) is the abstract interface (`include HTTP::Handler`; abstract `call` + `write`) every logger must inherit — but the whole abstraction is deprecated in favor of stdlib `Log`. — `src/kemal/base_log_handler.cr:3`
- `RequestLogHandler` (`request_log_handler.cr`) is the DEFAULT logger wired in by `config.setup_log_handler` (`config.cr:161-168`, only when `@logging`) — times `call_next` via `Time.measure` and emits status/method/resource/elapsed through stdlib `Log.info`; `elapsed_text` formats ms vs µs (`request_log_handler.cr:13-18`). — `src/kemal/request_log_handler.cr:6`

## Legacy / no-op loggers (all @[Deprecated])
- `LogHandler` (`log_handler.cr`) is the LEGACY `@[Deprecated]` STDOUT logger (same elapsed formatting, duplicated, `log_handler.cr:22-27`). — `src/kemal/log_handler.cr:22`
- `NullLogHandler` (`null_log_handler.cr`) is the `@[Deprecated]` Null-Object no-op returned by `Config#logger` when no custom logger is set (`config.cr:62-64`). — `src/kemal/null_log_handler.cr` (via config.cr:62)
- Config wires a custom legacy logger ahead of the default: `setup_log_handler` uses `@logger || RequestLogHandler.new` (`config.cr:164`), so a deprecated `BaseLogHandler` subclass still takes precedence when set. — `src/kemal/config.cr:164`

## Note (not drift — documented deprecation)
The legacy loggers are correctly `@[Deprecated]`-annotated with the replacement named ("Use standard library `Log`"). The duplicated `elapsed_text` in `request_log_handler.cr:13` and `log_handler.cr:22` is same-LOGIC duplication with IDENTICAL behavior — see `.ai/docs/issues.md` (IF-6 suppression: same-logic, no divergent named value-set).

## Cross-component edges
- logging ← core: `config.setup_log_handler` inserts `RequestLogHandler` second in the chain (right after `InitHandler`) when `@logging` is on.
- logging → core: `Config#logger` returns the `NullLogHandler` no-op default.
