# Component: helix-core

> BLIND re-derivation from source only. Every claim cites a `file:line` opened under `helix-core/`.
> Provenance: DeepInit EXTRACT stage, blind pass (architecture docs removed from tree). doc_in_inputs = false.

## Role

- The editor's text-editing core: it owns the document buffer model, selections, atomic edit transactions, undo history, and the tree-sitter-backed syntax engine, exposing them as a library crate with no UI/IO terminal concerns (helix-core/Cargo.toml:3 — "Helix editor core editing primitives"; helix-core/src/lib.rs:48 re-exports the `Rope` buffer; helix-core/src/syntax.rs:514 owns the `Syntax` engine).

## Dependencies (edges)

- helix-stdx — compile-time path dependency in the manifest (helix-core/Cargo.toml:19 `helix-stdx = { path = "../helix-stdx" }`); used pervasively for rope extension traits and ranges, e.g. `use helix_stdx::rope::RopeSliceExt` (helix-core/src/indent.rs:6), `pub use helix_stdx::range::Range` (helix-core/src/diagnostic.rs:4), and `helix_stdx::Url` (helix-core/src/uri.rs:56).
- helix-loader — compile-time path dependency (helix-core/Cargo.toml:20 `helix-loader = { path = "../helix-loader" }`); used to load grammars and language config: `use helix_loader::grammar::get_language` (helix-core/src/syntax.rs:17), `helix_loader::grammar::load_runtime_file(...)` (helix-core/src/syntax.rs:270), `helix_loader::config::default_lang_config` (helix-core/src/config.rs:8), and re-exported `pub use helix_loader::find_workspace` (helix-core/src/lib.rs:43).
- helix-parsec — compile-time path dependency (helix-core/Cargo.toml:21 `helix-parsec = { path = "../helix-parsec" }`); the parser-combinator toolkit used by the snippet parser via `use helix_parsec::*` (helix-core/src/snippets/parser.rs:29).
- (No outgoing edges to helix-view, helix-term, helix-tui, helix-lsp(-types), helix-event, helix-dap(-types), helix-vcs, or xtask: a tree-wide search of helix-core/src found zero references to any of those crate names — helix-core sits at the bottom of the dependency layering.)

## Data

- No database. Reads `.editorconfig` files from the filesystem by walking ancestor directories: `let editor_config_file = ancestor.join(".editorconfig")` then `fs::read_to_string(&editor_config_file)` (helix-core/src/editor_config.rs:48-49; the per-path EditorConfig is assembled in `EditorConfig::find` at helix-core/src/editor_config.rs:44).
- Reads language configuration (`languages.toml`) and tree-sitter runtime query files indirectly through helix-loader: built-in config via `helix_loader::config::default_lang_config` (helix-core/src/config.rs:8), user config via `helix_loader::config::user_lang_config(insecure)` (helix-core/src/config.rs:41), and per-language query files via `helix_loader::grammar::load_runtime_file(...)` (helix-core/src/syntax.rs:270).
- In-memory document buffer is a `ropey::Rope`, re-exported as the crate's buffer type (helix-core/src/lib.rs:48).
- The undo store is in-memory, unbounded: `History` is a `Vec<Revision>` plus a `current` index (helix-core/src/history.rs:51-54); each `Revision` keeps both the forward transaction and its inversion because delete transactions do not store deleted text (helix-core/src/history.rs:58-65), and the comment block notes the revision vector "is currently unbounded" (helix-core/src/history.rs:43-44).

## Boundary rules

- Bottom layer of the workspace: it depends only on helix-stdx, helix-loader, helix-parsec (helix-core/Cargo.toml:19-21) and references no higher-level helix crate anywhere in its source — so editor/view/terminal concerns must live above it, not in core.
- Strict Rust crate-graph DAG (workspace manifest, no cyclic crate deps possible under Cargo): helix-core is a `[workspace].members` entry (Cargo.toml root members list) consumed by higher crates rather than consuming them.
- The crate publishes its public surface explicitly through `lib.rs` re-exports (e.g. `Rope`/`RopeSlice` at helix-core/src/lib.rs:48, `Selection`/`Range` at helix-core/src/lib.rs:65, `Syntax` at helix-core/src/lib.rs:67, `Transaction`/`ChangeSet` at helix-core/src/lib.rs:73); `position` and `transaction` are private modules re-exported only through curated `pub use` (helix-core/src/lib.rs:24,33,58,73).

## Key facts

- Edits are modeled as an operational-transform-style `ChangeSet` of `Retain`/`Delete`/`Insert` operations with a length invariant: it stores `len` (required pre-edit doc length) and `len_after`, and "will refuse to apply changes unless it matches" (helix-core/src/transaction.rs:13-20, 72-78).
- `Selection` invariant: never empty — it always contains at least the primary range, stored as a `SmallVec<[Range; 1]>` plus a `primary_index` (helix-core/src/selection.rs:415-419).
- Syntax highlighting is delegated to the external `tree-house` / `tree_sitter` engine, wrapped by the crate's own `Syntax` (a thin wrapper over `tree_house::Syntax`, helix-core/src/syntax.rs:514-516) with a 500ms parse timeout `PARSE_TIMEOUT` (helix-core/src/syntax.rs:518); helix-core implements `tree_house::LanguageLoader` on its `Loader` (helix-core/src/syntax.rs:445-461).
- `Loader` is the language registry: it indexes languages by extension, shebang, and glob, holds per-language `LanguageServerConfiguration`, and stores theme scopes in an `ArcSwap<Vec<String>>` so scopes can be hot-swapped and grammars reconfigured at runtime (helix-core/src/syntax.rs:275-282, 435-442).
- Per-language queries (syntax/indent/textobject/tag/rainbow) are lazily compiled and cached behind `OnceCell` inside `LanguageData` (helix-core/src/syntax.rs:40-47).
- The buffer string type `Tendril` is a `SmartString<LazyCompact>` rather than std `String` (helix-core/src/lib.rs:51-53); `tendril` is explicitly commented out in favor of smartstring (helix-core/src/lib.rs:50).
- Rope-to-rope diffing uses the `imara-diff` library with the Histogram algorithm and an indent heuristic; `compare_ropes` returns a `Transaction` (helix-core/src/diff.rs:4, 141, 154).
- `Uri` currently models only local files: `Uri::File(Arc<Path>)` is the sole variant, with conversion to `helix_stdx::Url` (helix-core/src/uri.rs:14-15, 21-23).
- Unicode width is version-pinned `unicode-width = "=0.1.12"` to avoid rendering glitches, per an inline rationale comment (helix-core/Cargo.toml:27-32).
