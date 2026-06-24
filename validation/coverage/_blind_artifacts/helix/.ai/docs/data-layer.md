<!--
Provenance
- stage: blind-mirror-test (DeepInit EMIT/GENERATE)
- repo: helix@blind
- doc_in_inputs: false
- run: P5 Mirror-Test blind artifact
- date: 2026-06-13
- inputs: source files + Cargo manifests + directory layout only (architecture/design prose docs removed from tree)
-->

# Data layer / persistence

There is **no database** anywhere in the workspace. All persistence is the local filesystem (config, runtime assets, grammars, logs, trust store, document saves, themes), and most state is in-memory. The grounded data-store facts, by crate:

## helix-core

- No database. Reads `.editorconfig` files from the filesystem by walking ancestor dirs: `fs::read_to_string(ancestor.join(".editorconfig"))` (helix-core/src/editor_config.rs:48-49; EditorConfig::find at helix-core/src/editor_config.rs:44).
- Reads languages.toml + tree-sitter runtime query files via helix-loader: default_lang_config (helix-core/src/config.rs:8), user_lang_config (helix-core/src/config.rs:41), load_runtime_file (helix-core/src/syntax.rs:270).
- In-memory document buffer = ropey::Rope, re-exported as the crate buffer type (helix-core/src/lib.rs:48).
- In-memory unbounded undo store: History is Vec<Revision> + current index; each Revision keeps the forward transaction AND its inversion (delete txns don't store deleted text); the revision vector is unbounded (helix-core/src/history.rs:51-54,58-65,43-44).

## helix-view

- In-memory document registry `documents: BTreeMap<DocumentId, Document>` with monotonic non-recycling id allocation (helix-view/src/editor.rs:1194-1195,1964-1968).
- In-memory view/window layout Tree of Nodes in `slotmap::SlotMap<ViewId, Node>`, recomputed on resize/tree change (helix-view/src/tree.rs:1-18).
- Diagnostics store `Diagnostics = BTreeMap<Uri, Vec<(lsp::Diagnostic, DiagnosticProvider)>>` (helix-view/src/editor.rs:1188,1209).
- Registers store `HashMap<char, Vec<String>>`, with special registers backed by system/primary clipboard (helix-view/src/register.rs:24-32,12-23).
- File persistence (write): Document saves to disk via `to_writer` + `tokio::fs::File::create` with fsync and crash-safe backup-restore (helix-view/src/document.rs:630,986,1108-1109,1135-1156).
- Theme store (read): theme::Loader reads *.toml from on-disk theme_dirs via std::fs::read_to_string/read_dir; defaults via include_bytes! (helix-view/src/theme.rs:91,105,173,215,19,24).
- System clipboard I/O: external ClipboardProvider shells out via std::process::Command/spawn on Unix and clipboard_win API on Windows (helix-view/src/clipboard.rs:34-37,138,422,444,243,289).
- Save pipeline: per-document saves use `HashMap<DocumentId, UnboundedSender<...>>` feeding a SelectAll save_queue of in-flight save futures (helix-view/src/editor.rs:1199-1200).

Boundary: no database access — only local-file persistence (document save) and theme TOML reads (helix-view/src/document.rs:1108; helix-view/src/theme.rs:215).

## helix-term

- Reads & merges the global user TOML config file and the per-workspace local config file at startup (helix-term/src/config.rs:120-135).
- Writes the application log file from helix_loader::log_file (helix-term/src/main.rs:15).
- Reads/persists the workspace-trust store via WorkspaceTrust::load(true) then exclude_workspace/trust_workspace (helix-term/src/handlers/workspace_trust.rs:62-72).
- Reads runtime grammar/theme/tutor assets through the loader runtime dirs (helix-term/src/application.rs:100-101,139).
- In-process stores: prompt history register backing the picker (helix-term/src/ui/picker.rs:1137), process-global PROMPTED_WORKSPACES set (helix-term/src/handlers/workspace_trust.rs:16-17), runtime_local! JOB_QUEUE channel (helix-term/src/job.rs:14-16).

## helix-tui

- In-memory double screen buffer: Terminal holds `buffers: [Buffer; 2]` (current + previous), diffed each frame (helix-tui/src/terminal.rs:67).
- In-memory cell grid: each Buffer is a flat `Vec<Cell>` of length area.width*area.height (helix-tui/src/buffer.rs:167).
- Thread-local memoization cache `LAYOUT_CACHE: HashMap<(Rect,Layout),Vec<Rect>>` for split results (helix-tui/src/layout.rs:70).
- Reads process env vars TERM_PROGRAM/TERM/VTE_VERSION for capability detection (helix-tui/src/backend/crossterm.rs:27); the termina backend also reads TMUX (helix-tui/src/backend/termina.rs:105).
- Reads the terminfo capability database via termini::TermInfo::from_env (helix-tui/src/backend/crossterm.rs:77).
- Owns no DB/file persistence; the only OS write is the ANSI cursor-reset byte stream in restore (helix-tui/src/backend/crossterm.rs:210).

## helix-lsp

- In-memory server registry: `SlotMap<LanguageServerId, Arc<Client>>` + a by-name HashMap index (helix-lsp/src/lib.rs:580-587).
- In-memory per-request correlation map: `pending_requests Mutex<HashMap<jsonrpc::Id, Sender<Result<Value>>>>` (helix-lsp/src/transport.rs:46).
- In-memory progress cache: `LspProgressMap HashMap<LanguageServerId, HashMap<ProgressToken, ProgressStatus>>` (helix-lsp/src/lib.rs:785).
- In-memory watched-file glob state: `HashMap<LanguageServerId, ClientState{registered: HashMap<String, GlobSet>}>` in the file-event handler task (helix-lsp/src/file_event.rs:28-31).
- Reads (not writes) the filesystem for root-marker / required_root_patterns discovery: fs::read_dir (helix-lsp/src/lib.rs:1006), root_path.read_dir (helix-lsp/src/lib.rs:923).

## helix-dap

- No persistent/disk store. Per-Client in-memory state: Child process handle, socket, caps, `stack_frames HashMap<ThreadId,Vec<StackFrame>>`, thread_states, progress (helix-dap/src/client.rs:30-50).
- Transport request-correlation table `pending_requests: Mutex<HashMap<u64, Sender<Result<Response>>>>` keyed by request seq (helix-dap/src/transport.rs:56).
- Registry owns all live clients in `SlotMap<DebugAdapterId, Client>` + a SelectAll stream multiplexing all adapters' incoming messages (helix-dap/src/registry.rs:13-20).
- External I/O only: reads spawned adapter stdout/stdin/stderr or a TCP socket (helix-dap/src/client.rs:122-145).

## helix-event

- Process-global event Registry (events name->TypeId + per-event handler Vec) behind a RwLock in a runtime_local! static REGISTRY (helix-event/src/registry.rs:16-19,104-111).
- Global redraw-control state: REDRAW_NOTIFY (tokio Notify) + RENDER_LOCK (RwLock<>), both runtime_local! statics (helix-event/src/redraw.rs:10-21).
- Global status-message queue: OnceCell<Sender<StatusMessage>> MESSAGES static; setup makes the bounded(128) mpsc channel and returns the receiver (helix-event/src/status.rs:42-44,64-68).
- Per-AsyncHook bounded(128) tokio mpsc channel created per spawn, drained by a background task (helix-event/src/debounce.rs:25-37,39-61).
- TaskController/TaskHandle cancellation state: a single AtomicU64 packing 32-bit generation (low) + 32-bit running-count (high), shared via Arc<Shared> + a tokio Notify (helix-event/src/cancel.rs:24-40,56-71).

## helix-loader

- Runtime grammar libraries + queries under runtime/grammars/<name>.{so,dll,dylib,wasm} and runtime/queries/<lang>/<file> (read/written) — helix-loader/src/grammar.rs:75-77,718-721,16-26.
- Vendored grammar git source clones at <runtime>/grammars/sources/<grammar_id> (git init/fetch/checkout) — helix-loader/src/grammar.rs:338-345,357-364,369-390.
- config.toml + languages.toml (global config_dir, workspace.helix/, plus compile-time-embedded default via include_bytes!) — helix-loader/src/lib.rs:151-161; helix-loader/src/config.rs:6-9,13-34.
- Log file cache_dir/helix.log — helix-loader/src/lib.rs:163-165.
- Workspace-trust plaintext path stores data_dir/trusted_workspaces and data_dir/excluded_workspaces — helix-loader/src/lib.rs:167-173; helix-loader/src/workspace_trust.rs:31-62,65-103.

## helix-vcs

- On-disk git repository, read-only via gix: discovers repo upward, reads HEAD-commit blob as diff base, reads HEAD ref/short-hash name, enumerates worktree status (helix-vcs/src/git.rs:30,62,82,119).
- In-memory diff state `DiffInner{diff_base:Rope, doc:Rope, hunks:Vec<Hunk>}` behind `Arc<RwLock<...>>` written by the worker, read via DiffHandle (helix-vcs/src/diff.rs:31,40; helix-vcs/src/worker.rs:72).
- Reused line-interning cache InternedRopeLines that keeps base/doc lines interned to avoid per-diff reallocation (helix-vcs/src/diff/line_cache.rs:22).

## helix-stdx

- Process-global cached current working directory: `static CWD: RwLock<Option<PathBuf>>` (helix-stdx/src/env.rs:12), read by current_working_dir (helix-stdx/src/env.rs:17) and mutated by set_current_working_dir (helix-stdx/src/env.rs:42).
- Host environment reads (not persistence): std::env::var_os for PWD/CD (helix-stdx/src/env.rs:26-28) and $VAR expansion (helix-stdx/src/env.rs:161); current_dir/set_current_dir (helix-stdx/src/env.rs:24,44).
- Filesystem metadata/ACL reads for access checks and metadata copy: rustix::fs::access on Unix (helix-stdx/src/faccess.rs:59), GetNamedSecurityInfoW/AccessCheck on Windows (helix-stdx/src/faccess.rs:170,333); copy_metadata writes perms/owner/times to a destination file (helix-stdx/src/faccess.rs:93,415).

## xtask

- Reads workspace runtime assets: tree-sitter queries under runtime/queries/ (xtask/src/path.rs:18-20, walked by find_files xtask/src/helpers.rs:23-38) and themes under runtime/themes/ (xtask/src/path.rs:22-24, read at xtask/src/main.rs:252).
- Reads the indent corpus dir tests/indent/ — files named <language-id>.<ext>, enumerated/sorted/parsed (xtask/src/path.rs:26-28; xtask/src/main.rs:60,65-72,105).
- Writes generated Markdown into book/src/generated/: typable-cmd.md, static-cmd.md, lang-support.md via fs::write (xtask/src/docgen.rs:13-15,193-197; dir xtask/src/path.rs:10-12).
- Owns no DB/network persistence; all I/O is local filesystem (xtask/src/docgen.rs:193-197; xtask/src/main.rs:65,105,252).

## Crates with no data store

- helix-lsp-types — pure protocol-types crate, no data store (helix-lsp-types/Cargo.toml:12).
- helix-dap-types — owns NO runtime data store, file, or DB; the sole I/O surface is serde (de)serialization (helix-dap-types/src/lib.rs:6-9,19-23).
- helix-parsec — pure library, no I/O and no globals (helix-parsec/Cargo.toml:14; helix-parsec/src/lib.rs:1-575).
