<!--
Provenance
- stage: blind-mirror-test (DeepInit EMIT/GENERATE)
- repo: helix@blind
- doc_in_inputs: false
- run: P5 Mirror-Test blind artifact
- date: 2026-06-13
- inputs: source files + Cargo manifests + directory layout only (architecture/design prose docs removed from tree)
-->

# helix — AGENTS.md (lean tier)

## Architecture

Helix is a modal terminal text editor built as a single Cargo workspace (Cargo.toml:1-18, resolver "2") of 14 layered crates whose dependency graph is a strict DAG (Cargo bans cross-crate dependency cycles). The shipped binary is `hx`, produced by the lone default-member helix-term (Cargo.toml:20-22; helix-term/Cargo.toml:39-40), which runs on a multi-threaded Tokio async runtime (helix-term/src/main.rs:25 `#[tokio::main]`) and renders through a stacked-layer Compositor of `dyn Component` widgets (helix-term/src/compositor.rs:78-79). The data foundation is helix-core, which re-exports the ropey rope buffer as the text model (helix-core/src/lib.rs:48) and embeds a tree-sitter syntax engine (helix-core/src/syntax.rs); editor state is centralized in helix-view's Editor struct, holding Documents and Views in slotmap/BTreeMap registries keyed by DocumentId/ViewId (helix-view/src/editor.rs:1190-1199). Language tooling is split into client crates (helix-lsp for LSP, helix-dap for DAP), each over its own JSON-RPC transport (helix-lsp/src/jsonrpc.rs, helix-lsp/src/transport.rs:43) and paired with a pure protocol-types crate (helix-lsp-types, helix-dap-types). Cross-cutting concerns are factored into small leaf crates: helix-event (synchronous hook dispatch, helix-event/src/lib.rs:84), helix-loader (runtime-dir resolution + tree-sitter grammar build/fetch, helix-loader/src/lib.rs:2,38), helix-vcs (git integration), helix-tui (terminal rendering over termina/crossterm, helix-tui/Cargo.toml:15), plus the dependency-free helix-stdx and helix-parsec. The crate layering bottoms out at helix-stdx (no intra-workspace deps) and tops out at helix-term/xtask.

## Component registry

| component | role | path / anchor |
|-----------|------|---------------|
| helix-core | Editor text-editing core: Rope buffer, selections, ChangeSet edit transactions, undo history, tree-sitter syntax engine; no terminal/UI concerns | helix-core — helix-core/Cargo.toml:3; helix-core/src/lib.rs:48; helix-core/src/syntax.rs:514 |
| helix-view | Editor-state model + UI abstractions for backends: central Editor struct with Document/View registries, mode, registers, theme, diagnostics, handler wiring | helix-view — helix-view/src/editor.rs:1190-1262; helix-view/Cargo.toml:3 |
| helix-term | Application/binary crate producing the `hx` executable; top-level orchestrator: run loop, Compositor layer stack, Terminal backend, Editor state, job queue, LSP progress map | helix-term — Cargo.toml:6,21 (sole default-member); helix-term/Cargo.toml:39-41; helix-term/src/application.rs:70-82 |
| helix-tui | Immediate-mode terminal-UI rendering library: double-buffered cell grid behind a swappable Backend trait, Cassowary layout engine, styled-text model, widgets; emits only changed cells per frame | helix-tui — helix-tui/Cargo.toml:3; helix-tui/src/lib.rs:1 |
| helix-lsp-types | Pure leaf data-type crate modeling the Language Server Protocol message types as serde structures | helix-lsp-types — helix-lsp-types/Cargo.toml:12; helix-lsp-types/src/lib.rs:3-5 |
| helix-lsp | LSP client library: spawns each language server as a child process, speaks JSON-RPC 2.0 over stdio, exposes typed Client methods | helix-lsp — helix-lsp/Cargo.toml:3; helix-lsp/src/lib.rs:8 |
| helix-event | Decoupling layer: synchronous typed hooks dispatched on editor events, plus async/debounced hooks and main-loop message queues (redraw, status, job dispatch) | helix-event — helix-event/src/lib.rs:1-5,84 |
| helix-dap-types | Dependency-free pure-data-model crate for the Debug Adapter Protocol (DAP) types/requests/events | helix-dap-types — helix-dap-types/Cargo.toml:3; helix-dap-types/src/lib.rs:6-9 |
| helix-dap | DAP client library: spawns a debug-adapter process, speaks DAP over stdio or TCP, exposes typed request/event/registry APIs | helix-dap — helix-dap/Cargo.toml:3; helix-dap/src/client.rs:30 |
| helix-loader | Build-bootstrapping crate: resolves runtime/config/cache/data dirs, merges languages.toml, fetches/builds tree-sitter grammars; also the hx-loader bin | helix-loader — helix-loader/Cargo.toml:3; helix-loader/src/lib.rs:1-3; helix-loader/Cargo.toml:13-14 |
| helix-vcs | VCS-diff types: live async-recomputed line diff between a base text and the editing document, plus git working-tree status; git-feature-gated | helix-vcs — helix-vcs/src/lib.rs:1; helix-term/Cargo.toml:37 |
| helix-parsec | Self-contained parser-combinator library (Parser trait + primitives + combinators) over &str; no intra-workspace deps | helix-parsec — helix-parsec/Cargo.toml:3; helix-parsec/src/lib.rs:1-4 |
| helix-stdx | Leaf standard-library-extensions crate (env, faccess, path, range, rope, uri helpers); bottom of the DAG, no intra-workspace deps | helix-stdx — helix-stdx/Cargo.toml:3; helix-stdx/src/lib.rs:1-2 |
| xtask | Developer-tooling/automation binary (cargo-xtask pattern): docgen, query-check, indent-check, theme-check; not part of the shipped editor | xtask — Cargo.toml:17; xtask/src/main.rs:302-316 |

## Technical dependencies

(edges A -> B (kind) — file:line)

- helix-core -> helix-stdx (project-ref + import) — helix-core/Cargo.toml:19; helix-core/src/indent.rs:6; helix-core/src/uri.rs:56
- helix-core -> helix-loader (project-ref + import) — helix-core/Cargo.toml:20; helix-core/src/syntax.rs:17; helix-core/src/config.rs:8; helix-core/src/lib.rs:43
- helix-core -> helix-parsec (project-ref + import) — helix-core/Cargo.toml:21; helix-core/src/snippets/parser.rs:29
- helix-view -> helix-core (import / project-ref) — helix-view/Cargo.toml:20; helix-view/src/editor.rs:46-54; helix-view/src/lib.rs:85
- helix-view -> helix-event (queue-event / project-ref) — helix-view/Cargo.toml:21; helix-view/src/events.rs:2,7; helix-view/src/editor.rs:17,2046,2142
- helix-view -> helix-loader (import / project-ref) — helix-view/Cargo.toml:22; helix-view/src/theme.rs:9; helix-view/src/editor.rs:18,1746; helix-view/src/expansion.rs:286
- helix-view -> helix-lsp (import / runtime-call) — helix-view/Cargo.toml:23; helix-view/src/editor.rs:23,56,1208; helix-view/src/document.rs:16
- helix-view -> helix-dap (import / runtime-call) — helix-view/Cargo.toml:24; helix-view/src/editor.rs:55,1212,1271
- helix-view -> helix-vcs (import / project-ref) — helix-view/Cargo.toml:25; helix-view/src/editor.rs:19,1210; helix-view/src/document.rs:18
- helix-view -> helix-stdx (import / project-ref) — helix-view/Cargo.toml:19; helix-view/src/editor.rs:57,501,524; helix-view/src/document.rs:17; helix-view/src/clipboard.rs:108,119,135
- helix-view -> helix-tui (dev-dependency-only; no runtime edge, doctest refs) — helix-view/Cargo.toml:65; helix-view/src/graphics.rs:537,565
- helix-term -> helix-core (import) — helix-term/src/commands.rs:22-46
- helix-term -> helix-view (import; macro_use extern crate + types) — helix-term/src/lib.rs:1-2
- helix-term -> helix-lsp (import; LSP client + lsp:: types) — helix-term/src/application.rs:4-8
- helix-term -> helix-dap (import; DAP client + dap:: types) — helix-term/src/commands/dap.rs:7-9
- helix-term -> helix-vcs (import; feature-gated by default `git`) — helix-term/src/commands.rs:13
- helix-term -> helix-loader (import + build-dependency) — helix-term/Cargo.toml:99-100
- helix-term -> helix-event (import; event/hook system, redraw, runtime_local) — helix-term/src/handlers.rs:5
- helix-term -> helix-stdx (import; path/env/rope/Url helpers) — helix-term/src/application.rs:9
- helix-term -> helix-tui (import; renamed package `tui`: backends, Terminal, Surface) — helix-term/Cargo.toml:57
- helix-tui -> helix-view (project-ref path dep, feature=term) — helix-tui/Cargo.toml:18
- helix-tui -> helix-view (import; graphics::{Rect,Style,Color,Modifier,UnderlineStyle,CursorKind}, editor::Config, theme::Mode) — helix-tui/src/backend/mod.rs:7
- helix-tui -> helix-view (import; graphics + editor::Config conversion) — helix-tui/src/terminal.rs:5
- helix-tui -> helix-core (project-ref path dep) — helix-tui/Cargo.toml:19
- helix-tui -> helix-core (import; unicode::width::{UnicodeWidthChar,UnicodeWidthStr}) — helix-tui/src/buffer.rs:3
- helix-tui -> helix-core (import; line_ending::str_is_line_ending, unicode::width) — helix-tui/src/text.rs:49
- helix-lsp -> helix-lsp-types (import; path dep, re-exported as `lsp`) — helix-lsp/src/lib.rs:10
- helix-lsp -> helix-core (import; Rope/ChangeSet/Selection/Transaction, syntax config, LanguageServerId, diff::compare_ropes) — helix-lsp/src/lib.rs:16
- helix-lsp -> helix-stdx (runtime-call; env::which, path normalize, cwd) — helix-lsp/src/client.rs:226
- helix-lsp -> helix-loader (runtime-call find_workspace + import VERSION_AND_GIT_HASH) — helix-lsp/src/lib.rs:904
- helix-dap -> helix-dap-types (import; path-dep, glob re-export) — helix-dap/Cargo.toml:18; helix-dap/src/lib.rs:6
- helix-dap -> helix-dap-types (runtime-call; Request trait bound on every RPC) — helix-dap/src/client.rs:254
- helix-dap -> helix-core (import; syntax::config::DebugAdapterConfig, DebuggerQuirks) — helix-dap/Cargo.toml:17; helix-dap/src/client.rs:7
- helix-dap -> helix-stdx (import; env::which + ExecutableNotFoundError) — helix-dap/Cargo.toml:16; helix-dap/src/client.rs:120
- helix-loader -> helix-stdx (import) — helix-loader/src/lib.rs:5
- helix-loader -> helix-stdx (runtime-call; env::which("git")) — helix-loader/src/grammar.rs:87
- helix-loader -> helix-stdx (project-ref) — helix-loader/Cargo.toml:18
- helix-lsp-types -> helix-stdx (project-ref Cargo path dependency) — helix-lsp-types/Cargo.toml:27
- helix-lsp-types -> helix-stdx (import; re-export of the Url type) — helix-lsp-types/src/lib.rs:24
- helix-vcs -> helix-core (import; Rope/RopeSlice as the diffed text type) — helix-vcs/src/diff.rs:4; helix-vcs/Cargo.toml:13
- helix-vcs -> helix-event (runtime-call; lock_frame, request_redraw, RenderLockGuard) — helix-vcs/src/diff.rs:86,5; helix-vcs/src/worker.rs:169,195; helix-vcs/Cargo.toml:14
- xtask -> helix-term (import+runtime-call) — xtask/src/docgen.rs:5-7,59,72; xtask/Cargo.toml:15
- xtask -> helix-core (import+runtime-call) — xtask/src/main.rs:22-40,49-59; xtask/src/docgen.rs:133; xtask/Cargo.toml:16
- xtask -> helix-view (import+runtime-call) — xtask/src/docgen.rs:8,62-64; xtask/src/main.rs:246-263; xtask/Cargo.toml:17
- xtask -> helix-stdx (import+runtime-call; RopeSliceExt::first_non_whitespace_char) — xtask/src/main.rs:55,115,163; xtask/Cargo.toml:19
- xtask -> helix-loader (manifest-dep-only; no direct source use) — xtask/Cargo.toml:18
- helix-event -> (no intra-workspace dependencies; leaf) — helix-event/Cargo.toml:14-26
- helix-dap-types -> (no intra-workspace dependencies; leaf) — helix-dap-types/Cargo.toml:13-15
- helix-parsec -> (no intra-workspace dependencies; leaf) — helix-parsec/Cargo.toml:14
- helix-stdx -> (no intra-workspace dependencies; bottom of DAG) — helix-stdx/Cargo.toml:14-25

## Critical to know

- The workspace dependency graph is a strict acyclic DAG: helix-stdx is the bottom (no path = "../helix-*" deps, helix-stdx/Cargo.toml:14-25) and helix-term/xtask the top; Cargo's cross-crate cycle ban makes any intra-workspace import cycle structurally impossible (Cargo.toml:1-18).
- `hx` is produced by the lone default-member helix-term (Cargo.toml:20-22; helix-term/Cargo.toml:39-41); xtask is a dev-tooling binary built only when explicitly targeted and never shipped (Cargo.toml:17; xtask/src/main.rs:302-316).
- Async runtime is Tokio multi-thread, entered at helix-term/src/main.rs:25 `#[tokio::main]` (rt-multi-thread/process/fs features, helix-term/Cargo.toml:56) and reused by helix-lsp/helix-view/helix-dap/helix-event.
- The text model is the ropey Rope, re-exported as the crate buffer type at helix-core/src/lib.rs:48; the buffer string type is Tendril = SmartString<LazyCompact>, deliberately chosen over std String/tendril (helix-core/src/lib.rs:50-53).
- Edits are OT-style ChangeSets (Retain/Delete/Insert) with a length invariant — they store the required pre-edit doc length and refuse to apply unless it matches (helix-core/src/transaction.rs:13-20,72-78); a Selection is never empty, always holding at least the primary range (helix-core/src/selection.rs:415-419).
- Editor state is centralized in helix-view's Editor: documents are a BTreeMap<DocumentId, Document> with monotonic non-recycling ids (helix-view/src/editor.rs:1194-1195,1964-1968); the view/window layout is a slotmap::SlotMap<ViewId, Node> Tree with recyclable ids (helix-view/src/tree.rs:1-18,14).
- Config and the syntax loader are hot-swapped lock-free via arc-swap: Editor holds config: Arc<dyn DynAccess<Config>> and syn_loader: Arc<ArcSwap<syntax::Loader>> (helix-view/src/editor.rs:1215,1232); config itself is owned outside helix-view and injected (helix-view/src/editor.rs:1232).
- The UI is a back-to-front Compositor stack of Box<dyn Component> layers, each declaring its own size constraints (helix-term/src/compositor.rs:78-79,40-76); the model is Cursive-inspired and handle_event returns EventResult::{Ignored,Consumed} (helix-term/src/compositor.rs:12-76).
- Workspace-trust is a hard security gate: per-workspace local config is merged only when the workspace is Trusted, else only global config is used (helix-term/src/config.rs:128-134; helix-loader/src/config.rs:13-21), and language servers launch only after an explicit AllowAlways trust decision (helix-term/src/handlers/workspace_trust.rs:70-82).
- helix-tui renders by diffing: it holds two Buffers (current + previous) and flushes only changed cells, flipping the index each frame (helix-tui/src/terminal.rs:67,151,208); all terminal I/O goes through the cfg-selected Backend trait — TerminaBackend (non-Windows) / CrosstermBackend (Windows) / TestBackend (helix-tui/src/backend/mod.rs:12).
- LSP/DAP both frame messages with the LSP base protocol (`Content-Length: N\r\n\r\n` then N body bytes — helix-lsp/src/transport.rs:105,191; helix-dap/src/transport.rs:94-123) and use an asymmetric JSON stack: inbound parsed with sonic-rs, outbound serialized with serde_json (helix-lsp/src/transport.rs:139,172-175; helix-dap/src/transport.rs:131,161).
- Document saves are crash-safe: a backup is restored on write failure and removed on success, so a file is never left half-written (helix-view/src/document.rs:1135-1156).
- Tree-sitter grammars are fetched/compiled at build time (STRICT) unless HELIX_DISABLE_AUTO_GRAMMAR_BUILD is set (helix-term/build.rs:3-13); helix-loader resolves the runtime dir via a fixed 5-level precedence with a >=2-paths postcondition (helix-loader/src/lib.rs:31-78).
- helix-core depends ONLY on helix-stdx/helix-loader/helix-parsec and references no higher-level helix crate anywhere in its source (helix-core/Cargo.toml:19-21) — confirming the layering direction.
