<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: helix-view
 inputs: helix-view/src/**, helix-view/Cargo.toml
 doc_in_inputs: false
 derived_from: source + manifest only (prose architecture docs excluded by firewall)
 date: 2026-06-13
-->

# helix-view

## Role

- Provides the editor-state model and UI abstractions for backends: it owns the central `Editor` struct holding the `Document`/`View` registries plus mode, registers, theme, diagnostics and handler wiring (helix-view/src/editor.rs:1190-1262; Cargo.toml description "UI abstractions for use in backends" helix-view/Cargo.toml:3).

## Dependencies (edges)

- helix-core — manifest path dependency `helix-core = { path = "../helix-core" }` (helix-view/Cargo.toml:20); re-exports `Document`/`Editor` types built on core's `Rope`/`Selection`/`Transaction`/`ChangeSet` (helix-view/src/editor.rs:46-54), `align_view` calls `helix_core::char_idx_at_visual_offset` (helix-view/src/lib.rs:72,85), document model imports core `history::History`, `Syntax`, `Rope` (helix-view/src/document.rs:36-44).
- helix-event — manifest path dependency `helix-event = { path = "../helix-event" }` (helix-view/Cargo.toml:21); the editor's events are declared with the `events!` macro and dispatched via `helix_event::dispatch` (helix-view/src/events.rs:2,7; helix-view/src/editor.rs:17,2046,2142), and `TaskController` drives the document (helix-view/src/document.rs:15).
- helix-loader — manifest path dependency `helix-loader = { path = "../helix-loader" }` (helix-view/Cargo.toml:22); used for `merge_toml_values` in theme merge (helix-view/src/theme.rs:9), `find_workspace` (helix-view/src/expansion.rs:286), and `workspace_trust::TrustStatus`/`quick_query_workspace` (helix-view/src/editor.rs:18,1746).
- helix-lsp — manifest path dependency `helix-lsp = { path = "../helix-lsp" }` (helix-view/Cargo.toml:23); the editor holds `helix_lsp::Registry` for `language_servers` and consumes `Call`/`LanguageServerId`/`lsp` (helix-view/src/editor.rs:23,56,1208), document uses `helix_lsp::util::lsp_pos_to_pos` (helix-view/src/document.rs:16).
- helix-dap — manifest path dependency `helix-dap = { path = "../helix-dap" }` (helix-view/Cargo.toml:24); the editor holds `dap::registry::Registry` for `debug_adapters` and uses `registry::DebugAdapterId`/`dap::Payload` (helix-view/src/editor.rs:55,1212,1271).
- helix-vcs — manifest path dependency `helix-vcs = { path = "../helix-vcs" }` (helix-view/Cargo.toml:25); the editor holds `helix_vcs::DiffProviderRegistry` for `diff_providers` (helix-view/src/editor.rs:19,1210) and the document holds `DiffHandle`/`DiffProviderRegistry` (helix-view/src/document.rs:18).
- helix-stdx — manifest path dependency `helix-stdx = { path = "../helix-stdx" }` (helix-view/Cargo.toml:19); used for `path::canonicalize` (helix-view/src/editor.rs:57), `faccess::{copy_metadata, readonly}` (helix-view/src/document.rs:17), and `env::binary_exists`/`env_var_is_set` (helix-view/src/clipboard.rs:108,119,135; helix-view/src/editor.rs:501,524).
- helix-tui — **dev-dependency only** `helix-tui = { path = "../helix-tui" }` (helix-view/Cargo.toml:65); appears in source only inside doctest examples (helix-view/src/graphics.rs:537,565), so it is not a runtime/compile edge of the library.
- (no edge) helix-term, helix-lsp-types, helix-dap-types, helix-parsec, xtask — none are declared in helix-view/Cargo.toml and no `helix_term`/`helix_lsp_types`/`helix_dap_types`/`helix_parsec` reference exists in helix-view/src (verified by repo-wide grep; the only hits are doctest `helix_tui` lines graphics.rs:537,565). LSP/DAP wire types are reached transitively through helix-lsp / helix-dap, not directly.

## Data

- In-memory document registry: `documents: BTreeMap<DocumentId, Document>` with monotonic id allocation via `next_document_id`, incremented `unsafe` with `NonZeroUsize::new_unchecked(... + 1)` (helix-view/src/editor.rs:1194-1195,1964-1968).
- In-memory view/window layout: `Tree` of `Node`s in a `slotmap::SlotMap<ViewId, Node>`, recomputed on window resize/tree change (helix-view/src/tree.rs:1-18).
- Diagnostics store: `Diagnostics = BTreeMap<Uri, Vec<(lsp::Diagnostic, DiagnosticProvider)>>` held on the editor (helix-view/src/editor.rs:1188,1209).
- Registers store: `Registers` keyed by `char` over `HashMap<char, Vec<String>>`, including special registers backed by the system/primary clipboard (helix-view/src/register.rs:24-32,12-23).
- File persistence (write side): the `Document` saves buffer contents to disk through `to_writer` + `tokio::fs::File::create`, with fsync, symlink resolution, and crash-safe backup-restore-on-failure (helix-view/src/document.rs:630,970,986,1108-1109,1135-1156).
- Theme store (read side): `theme::Loader` reads `*.toml` theme files from on-disk `theme_dirs` via `std::fs::read_to_string` / `read_dir` (helix-view/src/theme.rs:91,100,105,173,215); built-in defaults are compiled in with `include_bytes!("../../theme.toml")` / `base16_theme.toml` (helix-view/src/theme.rs:19,24).
- System clipboard (OS-backed I/O): the external `ClipboardProvider` shells out to OS clipboard programs via `std::process::Command`/`spawn` on Unix and uses the `clipboard_win` Windows API directly on Windows (helix-view/src/clipboard.rs:34-37,138,422,444,243,289).
- Save pipeline: per-document `saves: HashMap<DocumentId, UnboundedSender<...>>` feeding a `SelectAll<Flatten<...>>` `save_queue` of in-flight save futures (helix-view/src/editor.rs:1199-1200).

## Boundary rules

- Library, not binary: helix-view is a `[package]` crate with no `[[bin]]`; `lib.rs` exposes the public module surface (`document`, `editor`, `view`, `tree`, `theme`, registers, handlers, events) (helix-view/src/lib.rs:1-19).
- Editor config is injected, not owned: the editor reads its `Config` through `Arc<dyn DynAccess<Config>>` rather than loading config files itself, keeping config ownership outside this crate (helix-view/src/editor.rs:1232,61-64).
- Handler implementations live upstream: `Handlers` fields are public "only because most of the actual implementation is in helix-term right now" — helix-view defines the handler wiring/event senders but the term layer drives them (helix-view/src/handlers.rs:20-30, comment line 21).
- Cross-crate event contract: editor lifecycle events are published on the helix-event bus via the `events!` macro and `dispatch`, so consumers couple to events rather than calling the editor directly (helix-view/src/events.rs:7-44; helix-view/src/editor.rs:17,2046,2142).
- DB security boundary: none — helix-view performs no database access; its only persistence is local files (document save) and theme TOML reads (helix-view/src/document.rs:1108; helix-view/src/theme.rs:215).
- Feature-gated terminal coupling: terminal/`crossterm`/`termina` support is behind the optional `term` feature, default off (helix-view/Cargo.toml:13-15,29,58); the wasm target falls back to a no-op clipboard (helix-view/src/clipboard.rs:36-37,40-50).

## Key facts

- `DocumentId` wraps `NonZeroUsize` specifically so `Option<DocumentId>` fits in one byte rather than two (helix-view/src/lib.rs:23-25); `ViewId` is a `slotmap::new_key_type!` key (helix-view/src/lib.rs:48-50).
- Id allocation is non-recycling/monotonic via `next_document_id` (a `BTreeMap` key space), distinct from views which use a recyclable slotmap (helix-view/src/editor.rs:1194-1195,1964-1968; helix-view/src/tree.rs:14).
- Shared mutable config/syntax-loader state uses `arc-swap`: `config: Arc<dyn DynAccess<Config>>` and `syn_loader: Arc<ArcSwap<syntax::Loader>>` allow lock-free hot-swap of config/grammars (helix-view/src/editor.rs:61-64,1215,1232).
- Theme previews are reversible: `last_theme` stashes the pre-preview theme so a cancelled preview restores it (helix-view/src/editor.rs:1217-1222).
- Document saves are crash-safe: on write failure the backup is copied/renamed back over the target, otherwise the backup is removed — never leaving the file half-written (helix-view/src/document.rs:1135-1156).
- Registers double as the clipboard interface: `*` (system) and `+` (primary) registers read/write through the injected `ClipboardProvider`, unifying yank/paste with OS clipboard (helix-view/src/register.rs:18-32; helix-view/src/clipboard.rs:7-11).
- Async runtime is tokio (multi-thread) with `parking_lot` mutexes and `futures_util` streams for the save queue and event loop (helix-view/Cargo.toml:38-41,51; helix-view/src/editor.rs:21-24,38-41,1200).
- The `Tree` is a recomputed layout, not authoritative geometry: node `area`/dimensions are recomputed on resize/tree change rather than stored as truth (helix-view/src/tree.rs:4-18).
<!-- DEEPINIT:END -->
