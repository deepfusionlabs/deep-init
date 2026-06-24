<!-- DEEPINIT:START -->
# Component: helix-lsp

> Provenance: DeepInit EXTRACT stage, BLIND re-derivation from code only. Run inputs: helix-lsp/Cargo.toml + helix-lsp/src/*.rs + root Cargo.toml. Date: 2026-06-13. Every claim cites a file:line opened inside p5_helix_blind/helix-lsp.

## Role

- The Language Server Protocol (LSP) **client** library for the editor: it spawns each language server as a child process and speaks JSON-RPC 2.0 to it over stdio, exposing typed request/notification methods (the crate's stated purpose, helix-lsp/Cargo.toml:3; the `Client` is the public entry point re-exported at helix-lsp/src/lib.rs:8).

## Dependencies (edges)

- **helix-lsp-types** — the LSP wire types; declared path dep (helix-lsp/Cargo.toml:19), re-exported as the crate's `lsp` module `pub use helix_lsp_types as lsp;` (helix-lsp/src/lib.rs:10) and used throughout (e.g. `helix_lsp_types::PartialResultParams`, helix-lsp/src/client.rs:1249). This is the dominant edge — almost every method takes/returns `lsp::*` types.
- **helix-core** — text/editor primitives: `Rope`, `ChangeSet`, `Selection`, `Transaction`, the `syntax::config::Language*` config types, `diagnostic::LanguageServerId`, and `diff::compare_ropes`. Declared path dep (helix-lsp/Cargo.toml:17); used at helix-lsp/src/lib.rs:16-18 (syntax config), helix-lsp/src/lib.rs:35 (`LanguageServerId` re-export), helix-lsp/src/lib.rs:430 (`helix_core::diff::compare_ropes`), helix-lsp/src/client.rs:14-18, and helix-lsp/src/client.rs:957 (`helix_core::Operation::*`).
- **helix-stdx** — std extensions: path normalization, `env::which` (PATH resolution of the server binary), `env::current_working_dir`, `env::ExecutableNotFoundError`. Declared path dep (helix-lsp/Cargo.toml:16); used at helix-lsp/src/lib.rs:19, helix-lsp/src/lib.rs:52, helix-lsp/src/lib.rs:995, helix-lsp/src/client.rs:20, and helix-lsp/src/client.rs:226 (`helix_stdx::env::which(cmd)`).
- **helix-loader** — workspace discovery + version string: `find_workspace` and `VERSION_AND_GIT_HASH`. Declared path dep (helix-lsp/Cargo.toml:18); used at helix-lsp/src/lib.rs:904 (`helix_loader::find_workspace`) and helix-lsp/src/client.rs:19 (`use helix_loader::VERSION_AND_GIT_HASH;`).
- **(no edge) helix-view / helix-term / helix-tui / helix-event / helix-dap / helix-dap-types / helix-vcs / helix-parsec / xtask** — none are declared in helix-lsp/Cargo.toml:15-34 and none are imported in src. The lone `helix_view` mention is a doc-comment reference only (`See helix_view::editor::Editor::refresh_language_servers`, helix-lsp/src/lib.rs:652), not a code dependency.

## Data

- Owns no on-disk store or database. State is in-memory only.
- **Server registry** — `Registry` holds a `SlotMap<LanguageServerId, Arc<Client>>` plus a `HashMap<LanguageServerName, Vec<Arc<Client>>>` index by name (helix-lsp/src/lib.rs:580-587); `LanguageServerId` is the slotmap key (helix-lsp/src/lib.rs:35).
- **Per-request correlation map** — the transport keeps `pending_requests: Mutex<HashMap<jsonrpc::Id, Sender<Result<Value>>>>` to route a server response back to the awaiting caller by request id (helix-lsp/src/transport.rs:46, populated helix-lsp/src/transport.rs:168-171, drained helix-lsp/src/transport.rs:236).
- **Progress map** — `LspProgressMap(HashMap<LanguageServerId, HashMap<lsp::ProgressToken, ProgressStatus>>)` caches `$/progress` reports per server/token (helix-lsp/src/lib.rs:785).
- **Watched-file glob state** — the file-event `Handler` task keeps `HashMap<LanguageServerId, ClientState>` where each `ClientState.registered` maps a registration id to a `globset::GlobSet` (helix-lsp/src/file_event.rs:28-31, helix-lsp/src/file_event.rs:91).
- Reads (not writes) the **filesystem**: scans dirs for root markers / `required_root_patterns` during workspace discovery (`fs::read_dir`, helix-lsp/src/lib.rs:1006; `root_path.read_dir`, helix-lsp/src/lib.rs:923).

## Boundary rules

- **The crate is the LSP boundary**: it converts between editor-side `helix_core` types and wire-side `lsp` types and nothing above it (e.g. `diagnostic_to_lsp_diagnostic`, helix-lsp/src/lib.rs:90; `pos_to_lsp_pos` / `lsp_pos_to_pos`, helix-lsp/src/lib.rs:146/223; `changeset_to_changes`, helix-lsp/src/client.rs:944).
- **Three-task ownership of the child process**: `Transport::start` spawns exactly three tokio tasks per server — `recv` (stdout), `err` (stderr), `send` (stdin) — and hands the caller channel ends, not the process (helix-lsp/src/transport.rs:73-87).
- **Pre-initialize queueing rule**: the `send` task buffers all non-`initialize`/`initialized` requests in `pending_messages` until the server signals initialized, then drains them; pre-init notifications are dropped and a pre-init `shutdown` ends the loop (helix-lsp/src/transport.rs:413-433, drain at helix-lsp/src/transport.rs:403).
- **Capability gating**: a feature is only used if `supports_feature` confirms the server advertised it, and `capabilities` panics if called before initialization completes (helix-lsp/src/client.rs:314, helix-lsp/src/client.rs:301-305).
- **Stop = tombstone**: `Registry::stop` drains a server's client vec but leaves the empty vec as a tombstone so `get` will not auto-restart a manually-stopped server (helix-lsp/src/lib.rs:692-707, honored in `get` at helix-lsp/src/lib.rs:723-725).
- **Strict server-message shape**: inbound `ServerMessage` is `#[serde(deny_unknown_fields)] #[serde(untagged)]` (Output | Call) (helix-lsp/src/transport.rs:33-39); but the JSON-RPC payload types deliberately **drop** `deny_unknown_fields` to tolerate non-conformant servers (helix-lsp/src/jsonrpc.rs:5-7).

## Key facts

- **Transport framing** = LSP base protocol: `Content-Length: N\r\n\r\n` header then N bytes of body; the reader loops headers until a bare `\r\n` (helix-lsp/src/transport.rs:105 /:191).
- **Serialization is asymmetric**: outbound uses `serde_json` (helix-lsp/src/transport.rs:172-175), inbound parsing uses `sonic-rs` (`sonic_rs::from_slice`, helix-lsp/src/transport.rs:139); both error types fold into the crate `Error::Parse` (helix-lsp/src/lib.rs:57-67).
- **Request ids** are a monotonic `AtomicU64` per client (`request_counter.fetch_add(.., Relaxed)`, helix-lsp/src/client.rs:281-284); a `call` registers a oneshot-style `channel::<Result<Value>>(1)` and awaits with a per-server `req_timeout` (helix-lsp/src/client.rs:457-499), yielding `Error::Timeout(id)` on expiry.
- **`OffsetEncoding`** (Utf8 / Utf16 / Utf32) defaults to **Utf16** per the LSP spec and drives every position/range conversion (helix-lsp/src/lib.rs:69-78); `pos_to_lsp_pos`/`lsp_pos_to_pos` branch on it (helix-lsp/src/lib.rs:184-218).
- **Capabilities are initialized exactly once** via `OnceCell` (`capabilities: OnceCell<lsp::ServerCapabilities>`, helix-lsp/src/client.rs:62; `get_or_try_init` in the async init, helix-lsp/src/lib.rs:953-959); `FileOperationsInterest` is similarly a `OnceLock` lazily derived from capabilities (helix-lsp/src/client.rs:63, helix-lsp/src/client.rs:307-310).
- **Injected lifecycle notifications**: the transport synthesizes `Initialized` (on init signal) and `Exit` (on stream close) `Notification`s into the client stream so downstream code runs after init/exit (helix-lsp/src/transport.rs:302-307, helix-lsp/src/transport.rs:388-393; the `Notification` enum comments at helix-lsp/src/lib.rs:537-540).
- **JSON-RPC id leniency** (interop): numeric ids accept floats with a zero fractional part (e.g. `4.0` -> `4`) to tolerate servers that serialize ints as floats (helix-lsp/src/jsonrpc.rs:110-135).
- **Overlapping-edit guard**: `generate_transaction_from_edits` sorts edits and drops any that overlap an earlier one (or fail to map) to avoid a `ChangeSet::from_changes` underflow panic — references issue #15514 / AUDIT-044/045 (helix-lsp/src/lib.rs:434-476).
- **File-watch handler holds `Weak<Client>`** so a registered server can still be dropped; a failed upgrade prunes the entry (helix-lsp/src/file_event.rs:29, helix-lsp/src/file_event.rs:105-107); always sends `FileChangeType::CHANGED` (helix-lsp/src/file_event.rs:121).
- **Tech choices**: async runtime is `tokio` multi-thread with process support (helix-lsp/Cargo.toml:28); shared client state uses `Arc` + `parking_lot::Mutex` (helix-lsp/src/client.rs:21,67) and `arc_swap::ArcSwap` for the syntax loader (helix-lsp/src/lib.rs:584); errors via `thiserror` (helix-lsp/src/lib.rs:37-55).
- Crate is a workspace member (root Cargo.toml:9), versioned 25.7.1 (root Cargo.toml:63), licensed MPL-2.0 (root Cargo.toml:69).
<!-- DEEPINIT:END -->
