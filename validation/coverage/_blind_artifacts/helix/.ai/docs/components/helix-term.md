<!--
DEEPINIT EXTRACT (BLIND) — component doc
stage: extract | component: helix-term | inputs: helix-term/ source + Cargo.toml | date: 2026-06-13
Derived from CODE ONLY; every bullet grounded to a file:line that was opened.
-->

# Component: helix-term

## Role

- The application / binary crate that produces the `hx` editor executable — `[[bin]] name = "hx", path = "src/main.rs"` with `default-run = "hx"` (helix-term/Cargo.toml:39-41, helix-term/Cargo.toml:5).
- It is the top-level orchestrator: the async entry point parses args, loads config + the language loader, then constructs and runs `Application` (helix-term/src/main.rs:25-147).
- `Application` owns the run loop, holding the `Compositor` (UI layer stack), the `Terminal` backend, the `Editor` state, the job queue and the LSP progress map (helix-term/src/application.rs:70-82).

## Dependencies (edges)

- helix-core — imports `diagnostic::Severity`, `pos_at_coords`, `syntax`, `Range`, `Selection` in the application; `commands.rs` pulls a large surface (`Rope`, `Selection`, `Transaction`, `Syntax`, `movement`, `textobject`, …) (helix-term/src/application.rs:3, helix-term/src/commands.rs:22-46; manifest helix-term/Cargo.toml:45).
- helix-view — `#[macro_use] extern crate helix_view` brings the `doc!`/`doc_mut!` macros crate-wide; `Editor`, `Document`, `View`, `editor::Config`, `tree::Layout`, `theme` are used throughout (helix-term/src/lib.rs:1-2, helix-term/src/application.rs:10-18, helix-term/src/commands.rs:47-58; manifest helix-term/Cargo.toml:47).
- helix-lsp — `lsp::{notification::Notification}`, `util::lsp_range_to_range`, `LanguageServerId`, `LspProgressMap`; LSP message handling lives in `Application::handle_language_server_message` (helix-term/src/application.rs:4-8, helix-term/src/application.rs:762; manifest helix-term/Cargo.toml:48). LSP protocol types are reached through this crate (`lsp::`), not a direct dep on helix-lsp-types.
- helix-dap — debug-adapter commands import `helix_dap::{self as dap, requests::TerminateArguments}` and use `dap::{StackFrame, Thread, ThreadStates}` (helix-term/src/commands/dap.rs:7-9, helix-term/src/commands/dap.rs:96; manifest helix-term/Cargo.toml:49). DAP protocol types are reached through this crate (`dap::`), not a direct dep on helix-dap-types.
- helix-vcs — `commands.rs` imports `helix_vcs::{FileChange, Hunk}` for diff/hunk navigation (helix-term/src/commands.rs:13; manifest helix-term/Cargo.toml:50). Gated by the default `git` feature which forwards to `helix-vcs/git` (helix-term/Cargo.toml:34, helix-term/Cargo.toml:37).
- helix-loader — runtime/config/grammar plumbing: `VERSION_AND_GIT_HASH`, `initialize_config_file`, `grammar::{fetch_grammars,build_grammars}`, `config_file`, `log_file`, `runtime_dirs`, `workspace_trust` (helix-term/src/main.rs:2, helix-term/src/main.rs:29, helix-term/src/main.rs:93-99, helix-term/src/config.rs:122-129; manifest helix-term/Cargo.toml:51). Also a build-dependency that runs `fetch_grammars`/`build_grammars` at compile time (helix-term/Cargo.toml:99-100, helix-term/build.rs:1-9).
- helix-event — frame/redraw + the event & hook system: `start_frame`, `request_redraw`, `dispatch`, `events!`/`register_event!`, `register_hook!`, `runtime_local!`, `AsyncHook` (helix-term/src/application.rs:267, helix-term/src/application.rs:336, helix-term/src/events.rs:1, helix-term/src/handlers.rs:5, helix-term/src/handlers/workspace_trust.rs:3, helix-term/src/job.rs:1-2; manifest helix-term/Cargo.toml:46). The `integration` feature forwards to `helix-event/integration_test` (helix-term/Cargo.toml:36).
- helix-stdx — path/env/rope helpers: `path::get_relative_path`, `env::set_current_working_dir`, `Url`, `path::canonicalize`, `rope::RopeSliceExt` (helix-term/src/application.rs:9, helix-term/src/main.rs:108, helix-term/src/lib.rs:24, helix-term/src/args.rs:36, helix-term/src/commands.rs:9-12; manifest helix-term/Cargo.toml:44).
- helix-tui — depended on as `tui` (package rename) with `default-features = false, features = ["termina","crossterm"]`; supplies `backend::{Backend,TerminaBackend,CrosstermBackend,TestBackend}`, `terminal::Terminal`, `buffer::Buffer as Surface`, widgets/text (helix-term/Cargo.toml:57, helix-term/src/application.rs:20-68, helix-term/src/compositor.rs:7, helix-term/src/commands.rs:16-19).
- NO direct edge found to **helix-lsp-types** (reached transitively via helix-lsp `lsp::`), **helix-dap-types** (via helix-dap `dap::`), **helix-parsec** (no `helix_parsec`/`parsec` reference in src), or **xtask** (no reference in src; not in `[dependencies]`) — manifest dependency list is helix-term/Cargo.toml:44-51.

## Data

- Reads the user TOML config file and the per-workspace config file at startup (`config_file` global + `workspace_config_file` local), merging them (helix-term/src/config.rs:120-135).
- Writes the log file initialized from `helix_loader::log_file` (helix-term/src/main.rs:15, helix-term/src/logging.rs via `logging::init_file`).
- Reads/writes the workspace-trust store: `WorkspaceTrust::load(true)` then `exclude_workspace` / `trust_workspace` to persist the user's trust decision (helix-term/src/handlers/workspace_trust.rs:62-72).
- Reads runtime grammar/theme/tutor assets via the loader (`runtime_file`, `runtime_dirs`, `runtime_file(Path::new("tutor"))`) (helix-term/src/application.rs:100-101, helix-term/src/application.rs:139).
- In-process state stores (not files): the prompt history register backing the picker query (helix-term/src/ui/picker.rs:1137); a process-global `PROMPTED_WORKSPACES` set guarding repeat trust prompts (helix-term/src/handlers/workspace_trust.rs:16-17); the `runtime_local!` `JOB_QUEUE` channel sender (helix-term/src/job.rs:14-16). `config-file`/`config-reload`/`log-open` typed commands open these stores as editor buffers (helix-term/src/commands/typed.rs:2468-2491).

## Boundary rules

- Owned-region / layering: it is the UI host. The `Compositor` is a stack of `Box<dyn Component>` layers each declaring its own size constraints, rendered back-to-front (helix-term/src/compositor.rs:78-79, helix-term/src/compositor.rs:1, helix-term/src/compositor.rs:40-76).
- Trust gate before local config + language servers: the per-workspace config is only merged when `quick_query_workspace(...)` returns `Trusted`, otherwise only the global config is used (helix-term/src/config.rs:128-134); language servers are launched only after an explicit `AllowAlways` trust decision (helix-term/src/handlers/workspace_trust.rs:70-82).
- Working directory must be set early (before `Application::new`) so the correct config loads — an explicit ordering invariant noted in code (helix-term/src/main.rs:105-116).
- Config validation is strict: `ConfigRaw` uses `#[serde(deny_unknown_fields)]`, so unknown config keys are rejected (helix-term/src/config.rs:19-25).
- Event registration is centralized: `events::register` must run during handler setup, and every hook is wired through `handlers::setup` → `register_hooks` (helix-term/src/handlers.rs:30, helix-term/src/handlers.rs:50-61, helix-term/src/events.rs:17-30).

## Key facts

- Async runtime is **Tokio** multi-thread; `main_impl` is `#[tokio::main]` and the dep enables `rt-multi-thread`, `process`, `fs`, `parking_lot` features (helix-term/src/main.rs:25-26, helix-term/Cargo.toml:56).
- Config is hot-swappable: stored as `Arc<ArcSwap<Config>>` and handed to the `Editor` and keymaps via `arc_swap::access::Map` projections (`config.editor`, `config.keys`), so a reload swaps the pointer without rebuilding the editor (helix-term/src/application.rs:75, helix-term/src/application.rs:117-133).
- The terminal backend is selected at compile time by `cfg`: Termina on non-Windows, Crossterm on Windows, `TestBackend` under the `integration` feature (helix-term/src/application.rs:47-61; Windows crossterm dep helix-term/Cargo.toml:92-93).
- Signal handling is platform-split: real `signal_hook_tokio::Signals` on non-Windows, an empty stream stub on Windows (helix-term/src/application.rs:42-45; non-Windows deps helix-term/Cargo.toml:95-97).
- The `Compositor`/`Component` model is "Cursive-inspired": each `Component` implements `handle_event`/`render`/`required_size`, and event handling returns `EventResult::{Ignored,Consumed}` carrying an optional `Callback` (helix-term/src/compositor.rs:12-76).
- The `Config` struct is the term-layer aggregate of theme + keymaps + the view-layer editor config; default keymaps come from `keymap::default` (helix-term/src/config.rs:12-35, helix-term/src/keymap/default.rs:7).
- Grammars are fetched/compiled at build time unless `HELIX_DISABLE_AUTO_GRAMMAR_BUILD` is set, and the build runs in STRICT mode (helix-term/build.rs:3-9); on Windows the build also links an icon into the exe via the SDK `rc.exe` (helix-term/build.rs:12-13, helix-term/build.rs:21-35).
- Custom binary/text detection (`is_binary`) replaces the `content_inspector` crate: BOM ⇒ text, else a NUL in the first 1 KiB or `%PDF`/`\x89PNG` magic ⇒ binary (helix-term/src/lib.rs:58-74).
- External URLs are opened out-of-process via the `open` crate, wrapped as a job `Callback` (helix-term/src/lib.rs:101-117, helix-term/Cargo.toml:80).
- The fuzzy file picker is built on `nucleo` plus the `ignore`/`grep-*` crates, and always skips VCS dirs (`.git/.pijul/.jj/.hg/.svn`) in `filter_picker_entry` (helix-term/Cargo.toml:70-74, helix-term/src/lib.rs:77-99).
