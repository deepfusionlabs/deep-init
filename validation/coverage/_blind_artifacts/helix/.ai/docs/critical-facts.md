<!--
Provenance
- stage: blind-mirror-test (DeepInit EMIT/GENERATE)
- repo: helix@blind
- doc_in_inputs: false
- run: P5 Mirror-Test blind artifact
- date: 2026-06-13
- inputs: source files + Cargo manifests + directory layout only (architecture/design prose docs removed from tree)
-->

# Critical facts — invariants, boundary rules, tech choices

## Technology choices

- Language/build: Rust 2021 edition, Cargo workspace with resolver "2", workspace version 25.7.1 (Cargo.toml:2,62-64; helix-core/Cargo.toml edition via [workspace.package]).
- Async runtime: Tokio multi-threaded (features rt-multi-thread, io-util, process, fs, macros) — helix-term/Cargo.toml:56, entered at helix-term/src/main.rs:25; also used by helix-lsp/Cargo.toml:28, helix-view/Cargo.toml:38, helix-dap/Cargo.toml:24, helix-event/Cargo.toml:17.
- Text buffer model: ropey rope data structure with the SIMD feature (Cargo.toml:48 ropey workspace dep; re-exported at helix-core/src/lib.rs:48).
- Syntax engine: tree-sitter via the tree-house crate (Cargo.toml:41; helix-core/Cargo.toml:35); grammars fetched/built by helix-loader (helix-loader/src/lib.rs:2 mod grammar).
- Terminal backend: termina + crossterm, both default features of helix-tui (helix-tui/Cargo.toml:15,25,31).
- LSP transport: custom JSON-RPC over a Tokio transport with a pending-request map (helix-lsp/src/jsonrpc.rs; helix-lsp/src/transport.rs:43-46), serde_json for serialization (helix-lsp/Cargo.toml:27), typed by helix-lsp-types (helix-lsp-types/Cargo.toml:12).
- DAP transport: Debug Adapter Protocol client (helix-dap/Cargo.toml:3) typed by helix-dap-types (helix-dap-types/Cargo.toml:3).
- Editor state containers: slotmap + BTreeMap document/view registries and arc-swap for config (helix-view/Cargo.toml:36,42; helix-view/src/editor.rs:1190-1199).
- Fuzzy matching: nucleo matcher (Cargo.toml:42; helix-core/Cargo.toml:55).
- UI architecture: stacked-layer Compositor over a `dyn Component` trait (helix-term/src/compositor.rs:40,78-79).
- Event model: synchronous hook dispatch with optional AsyncHook debouncing (helix-event/src/lib.rs:36,84).
- Config format: TOML (Cargo.toml:54 toml workspace dep; helix-core/Cargo.toml:46).
- Concurrency primitives: parking_lot locks (Cargo.toml:50) enabled across the Tokio feature sets.
- License: MPL-2.0 (Cargo.toml:69 [workspace.package].license).

## Key invariants

- Strict acyclic crate DAG: the workspace is a single Cargo workspace (Cargo.toml:1-18, resolver "2") and Cargo bans cross-crate dependency cycles, so no intra-workspace import cycle is possible; helix-stdx is the bottom (no path deps, helix-stdx/Cargo.toml:14-25) and helix-term/xtask the top.
- ChangeSet length invariant: edits are modeled as an OT-style ChangeSet of Retain/Delete/Insert operations storing len (required pre-edit doc length) + len_after, and the change set refuses to apply unless len matches (helix-core/src/transaction.rs:13-20,72-78).
- Selection-never-empty invariant: a Selection always contains at least the primary range; stored as SmallVec<[Range;1]> + primary_index (helix-core/src/selection.rs:415-419).
- Document id allocation is monotonic/non-recycling (BTreeMap key); View ids are recyclable (slotmap) (helix-view/src/editor.rs:1964-1968; helix-view/src/tree.rs:14). DocumentId wraps NonZeroUsize so Option<DocumentId> fits in one byte; ViewId is a slotmap new_key_type! key (helix-view/src/lib.rs:23-25,48-50).
- Crash-safe document saves: on write failure the backup is copied/renamed back, otherwise removed — a file is never left half-written (helix-view/src/document.rs:1135-1156).
- Syntax parse timeout: the syntax engine uses a 500ms PARSE_TIMEOUT (helix-core/src/syntax.rs:518); the crate's Syntax is a thin wrapper over tree_house::Syntax (helix-core/src/syntax.rs:514-516).
- LSP OffsetEncoding (Utf8/Utf16/Utf32) defaults to Utf16 per the LSP spec and drives all position/range conversion (helix-lsp/src/lib.rs:69-78,184-218).
- LSP request ids are a monotonic AtomicU64 per client; each call awaits a channel with a per-server req_timeout, yielding Error::Timeout(id) on expiry (helix-lsp/src/client.rs:281-284,457-499).
- DAP sequence invariant: first seq is 1, each subsequent +1, via an AtomicU64 counter (helix-dap/src/client.rs:235-241); DAP RPC has a hard-coded 20-second timeout (helix-dap/src/client.rs:284-286).
- TUI double-buffered diff rendering: Terminal::flush diffs previous vs current buffer and sends only changed cells; after each draw the back buffer is reset and the current index flips (self.current = 1 - self.current) (helix-tui/src/terminal.rs:151,208). Default terminal geometry is 80x24 (DEFAULT_TERMINAL_SIZE) when the backend cannot report a size (helix-tui/src/terminal.rs:77,91).
- Event uniqueness: event types must be unique by Event::ID (their type name); duplicate registration panics, and the registry enforces TypeId matching on register and dispatch (helix-event/src/registry.rs:25-40,53-64,85-93). status::setup must be called exactly once at startup (calling twice panics) and is the only way to obtain the message receiver (helix-event/src/status.rs:59-68).
- A hook returning Err is logged and routed to status::report_blocking; a hook failure never aborts the remaining hooks for that event (helix-event/src/registry.rs:94-101).
- Grammars are fetched/compiled at build time (STRICT) unless HELIX_DISABLE_AUTO_GRAMMAR_BUILD is set; helix-loader resolves the runtime dir via a fixed 5-level precedence with a >=2-paths postcondition (helix-term/build.rs:3-13; helix-loader/src/lib.rs:31-78).

## Boundary rules

- Workspace-trust gate (config): per-workspace local config is merged only when the workspace is Trusted (or insecure==true), else only global config is used (helix-term/src/config.rs:128-134; helix-loader/src/config.rs:13-21; helix-loader/src/workspace_trust.rs:142-159).
- Workspace-trust gate (language servers): servers are launched only after an explicit AllowAlways trust decision (helix-term/src/handlers/workspace_trust.rs:70-82).
- Strict config validation: ConfigRaw is #[serde(deny_unknown_fields)], so unknown config keys are rejected (helix-term/src/config.rs:19-25).
- Working-directory ordering invariant: cwd must be set before Application::new so the correct config loads (helix-term/src/main.rs:105-116).
- helix-core is the bottom UI-free layer: it depends ONLY on helix-stdx/helix-loader/helix-parsec (helix-core/Cargo.toml:19-21) and references no higher-level helix crate anywhere in src.
- helix-view config is injected, not owned: read through Arc<dyn DynAccess<Config>>; config-file ownership stays outside this crate (helix-view/src/editor.rs:1232). Terminal coupling is feature-gated behind the optional non-default `term` feature; wasm falls back to a no-op clipboard (helix-view/Cargo.toml:13-15,29,58; helix-view/src/clipboard.rs:36-37,40-50).
- helix-tui terminal-I/O boundary: all terminal I/O goes through the `Backend` trait, never directly; the concrete backend is chosen by cfg — TerminaBackend (non-Windows), CrosstermBackend (Windows), TestBackend always (helix-tui/src/backend/mod.rs:12). Widgets never touch the terminal — they render only into the intermediate Buffer (helix-tui/src/buffer.rs:139; helix-tui/src/widgets/mod.rs:46). Config flows one-way: helix_view editor Config is converted into the TUI's own terminal::Config via From<&EditorConfig> (helix-tui/src/terminal.rs:31).
- helix-lsp is the LSP boundary: it converts editor-side helix_core types <-> wire-side lsp types (helix-lsp/src/lib.rs:90,146,223; helix-lsp/src/client.rs:944) and spawns exactly three tokio tasks per server (recv/err/send) (helix-lsp/src/transport.rs:73-87). Capability gating: a feature is used only if supports_feature confirms it (helix-lsp/src/client.rs:314); a stopped server is tombstoned so get will not auto-restart it (helix-lsp/src/lib.rs:692-707,723-725).
- helix-dap separation of protocol types from behavior: helix-dap-types holds only the data model and never reaches back into a consumer; the transport/client logic lives in helix-dap (helix-dap/src/client.rs:254,301; helix-dap/src/lib.rs:6). The transport recv/send task pair is the only code touching raw streams (helix-dap/src/client.rs:79-100; helix-dap/src/transport.rs:60-83).
- helix-event hook discipline: hooks run synchronously with only &mut Event; stateful/expensive/debounced work must move to an AsyncHook background tokio task (helix-event/src/lib.rs:13-23; helix-event/src/debounce.rs:9-37). Synchronous hooks must use the crate's send_blocking (not tokio blocking_send), which drops a message after a 10ms timeout rather than freezing the editor (helix-event/src/lib.rs:18-22; helix-event/src/debounce.rs:63-70).
- helix-loader trust gate + write-once init: user/workspace languages.toml is merged only when the workspace is Trusted (helix-loader/src/config.rs:13-21); RUNTIME_DIRS is a Lazy<Vec<PathBuf>> and CONFIG_FILE/LOG_FILE are OnceCells set via initialize_* (helix-loader/src/lib.rs:12-29,143-149).
- helix-vcs provider boundary: the git module compiles only under #[cfg(feature="git")], else DiffProvider::None bails "No diff support compiled in" (helix-vcs/src/lib.rs:12,109); helix-term gates the crate via git=["helix-vcs/git"] (helix-term/Cargo.toml:37). All VCS access funnels through DiffProviderRegistry, which degrades per-provider errors to log::debug!+None so callers get Option, never a hard failure (helix-vcs/src/lib.rs:33,39).
- helix-parsec zero-copy / leaf boundary: parsers never allocate from or own the input — success returns a sub-slice plus the remaining suffix, failure returns the original input unchanged (helix-parsec/src/lib.rs:13-16,78-82); the crate has no outbound edges, no I/O, and no globals (helix-parsec/Cargo.toml:14).
- helix-stdx bottom-of-DAG boundary: a workspace member (Cargo.toml:16) whose [dependencies] contain no path = "../helix-*" entry, so it imports no sibling crate (helix-stdx/Cargo.toml:14-25); public surface = the modules re-exported in lib.rs (env, faccess, path, range, rope, uri) plus flattened Range and Url (helix-stdx/src/lib.rs:4-12).
- xtask build boundary: listed last in [workspace].members, separate from default-members=[helix-term], so it is built only when explicitly targeted (Cargo.toml:3-22); nothing depends back on it (Cargo.toml:20-22). Its CLI returns Err("Invalid task name") on an unknown task rather than panicking (xtask/src/main.rs:302-313).

## Notable design facts

- The buffer string type is Tendril = SmartString<LazyCompact>, not std String; tendril is explicitly commented out in favor of smartstring (helix-core/src/lib.rs:50-53).
- Config is hot-swappable, stored as Arc<ArcSwap<Config>> and projected to Editor/keymaps via arc_swap::access::Map so a reload swaps the pointer (helix-term/src/application.rs:75,117-133); helix-view likewise hot-swaps config/syntax-loader via arc-swap (helix-view/src/editor.rs:1215,1232).
- The Compositor/Component model is Cursive-inspired; handle_event returns EventResult::{Ignored,Consumed} carrying an optional Callback (helix-term/src/compositor.rs:12-76).
- Custom is_binary detection replaces content_inspector: BOM => text, else NUL in the first 1KiB or %PDF/PNG magic => binary (helix-term/src/lib.rs:58-74).
- The file picker is built on nucleo + ignore/grep-* and always skips VCS dirs (.git/.pijul/.jj/.hg/.svn) (helix-term/Cargo.toml:70-74; helix-term/src/lib.rs:77-99).
- LSP/DAP JSON is asymmetric: outbound serde_json, inbound sonic-rs for speed; both fold into Error::Parse (helix-lsp/src/transport.rs:139,172-175; helix-lsp/src/lib.rs:57-67; helix-dap/src/transport.rs:131,161; helix-dap/src/lib.rs:32-42).
- LSP transport injects synthetic Initialized (on init) and Exit (on stream close) notifications so downstream code runs after init/exit (helix-lsp/src/transport.rs:302-307,388-393); pre-initialize requests are buffered until the server signals initialized (helix-lsp/src/transport.rs:413-433).
- DAP TCP startup waits with a fixed 500ms sleep before connecting — a timing assumption, not a readiness handshake (helix-dap/src/client.rs:184); process-reaping differs by transport (stdio kill_on_drop(true); tcp does not) (helix-dap/src/client.rs:128,180-181).
- helix-vcs diff is hard-coded to the Histogram algorithm with an indent heuristic, skips when a side exceeds MAX_DIFF_LINES=64*u16::MAX, and uses debounce tuning (1ms sync / 96ms async) (helix-vcs/src/diff.rs:121,122-124,117-120).
- helix-stdx ships a hand-rolled minimal RFC3986 Url newtype over String instead of the url crate, because LSP uses RFC3986 (not WHATWG) percent-encoding (helix-stdx/src/uri.rs:1-7,45-46); path::normalize normalizes WITHOUT resolving symlinks or requiring the path to exist (helix-stdx/src/path.rs:60-63,130-134).
- helix-lsp-types is #![forbid(unsafe_code)] and isolates unstable LSP extensions behind an opt-in `proposed` Cargo feature (helix-lsp-types/src/lib.rs:18; helix-lsp-types/Cargo.toml:29-33); it is edition 2018, version 0.95.1, MIT, a fork of gluon-lang/lsp-types (helix-lsp-types/Cargo.toml:3,11,14,21).
- helix-loader's build.rs injects VERSION_AND_GIT_HASH (CalVer + 8-char git hash) and BUILD_TARGET as compile-time env vars (helix-loader/build.rs:5-39,60-81; consumed at helix-loader/src/lib.rs:10).
