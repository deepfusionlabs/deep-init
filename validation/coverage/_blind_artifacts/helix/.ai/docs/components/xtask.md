<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: xtask
 path: xtask
 inputs: xtask/Cargo.toml, xtask/src/main.rs, xtask/src/docgen.rs, xtask/src/helpers.rs, xtask/src/path.rs, Cargo.toml (workspace)
 doc_in_inputs: false
 repo_sha: undefined (prose architecture docs removed prior to analysis)
 date: 2026-06-13
-->

# Component: xtask

## Role

- A developer-tooling / automation binary crate (the `cargo xtask` pattern) that runs maintenance tasks for the workspace — `docgen`, `query-check`, `indent-check`, `theme-check` — dispatched by name from CLI args, not part of the shipped editor (xtask/src/main.rs:302-316).

## Dependencies (edges)

- helix-term — import + runtime calls: pulls `MappableCommand`, `TYPABLE_COMMAND_LIST`, `health::TsFeature` (xtask/src/docgen.rs:5-7) and `keymap::default` / `MappableCommand::STATIC_COMMAND_LIST` to generate the command reference docs (xtask/src/docgen.rs:59, 72); `TsFeature` is also imported in helpers (xtask/src/helpers.rs:4); declared dep at xtask/Cargo.toml:15.
- helix-core — import + runtime calls: `helix_core::config::default_lang_loader` and `LanguageData` syntax/query compilation in `querycheck` (xtask/src/main.rs:22-40), the same loader + `indent::{is_opaque_interior, is_outdent_token_at, treesitter_indent_for_pos, IndentStyle}` and `Syntax` in `indentcheck` (xtask/src/main.rs:49-59), and `default_lang_config` in docgen (xtask/src/docgen.rs:133); declared dep at xtask/Cargo.toml:16.
- helix-view — import + runtime calls: `helix_view::document::Mode` keyed into the keymap (xtask/src/docgen.rs:8, 62-64) and `helix_view::theme::Loader` (`Loader::new`, `read_names`, `load_with_warnings`) in `themecheck` (xtask/src/main.rs:246-263); declared dep at xtask/Cargo.toml:17.
- helix-stdx — import + runtime call: `helix_stdx::rope::RopeSliceExt` (the `first_non_whitespace_char` extension trait) used in `indentcheck` (xtask/src/main.rs:55, 115, 163); declared dep at xtask/Cargo.toml:19.
- helix-loader — declared manifest dependency only (xtask/Cargo.toml:18); no direct `helix_loader::` reference found in xtask/src/*.rs (likely pulled transitively / for the runtime-resolution side effects of the other crates).
- xtask (internal) — `main` wires three internal modules `docgen`, `helpers`, `path` (xtask/src/main.rs:1-3); docgen depends on internal `helpers` and `path` (xtask/src/docgen.rs:1-2); helpers depends on internal `path` (xtask/src/helpers.rs:3).
- (no edges to helix-tui, helix-lsp-types, helix-lsp, helix-event, helix-dap-types, helix-dap, helix-vcs, helix-parsec — none imported or declared in this crate; manifest deps are only the five helix-* listed above, xtask/Cargo.toml:15-19.)

## Data

- Reads the workspace runtime tree as input data: tree-sitter queries under `runtime/queries/` (xtask/src/path.rs:18-20, walked by `find_files` in xtask/src/helpers.rs:23-38) and theme files under `runtime/themes/` (xtask/src/path.rs:22-24, read by `Loader::read_names` at xtask/src/main.rs:252).
- Reads the indent corpus directory `tests/indent/` — files named `<language-id>.<ext>` enumerated and sorted, then parsed per file (xtask/src/path.rs:26-28; xtask/src/main.rs:60, 65-72, 105).
- Writes generated Markdown into `book/src/generated/`: `typable-cmd.md`, `static-cmd.md`, `lang-support.md` via `fs::write` (xtask/src/docgen.rs:13-15, 193-197; output dir xtask/src/path.rs:10-12).
- Owns no database / network persistence — all I/O is local filesystem reads of the repo tree plus the three generated doc files (xtask/src/docgen.rs:193-197; xtask/src/main.rs:65, 105, 252).

## Boundary rules

- Workspace member: `xtask` is the last entry in the `[workspace] members` list, separate from `default-members = ["helix-term"]`, so it is built only when explicitly targeted, never by a default `cargo build` (Cargo.toml:3-22).
- Build-manifest DAG (hard-ban regime): all inter-crate edges are declared via path dependencies in the manifest (xtask/Cargo.toml:15-19); xtask is a top-of-graph consumer — nothing in the workspace depends back on it (it is absent from every other crate's deps and not in `default-members`, Cargo.toml:20-22), so it introduces no cycle.
- Locates the project root from its own compile-time manifest location: `project_root` = `CARGO_MANIFEST_DIR`'s parent (xtask/src/path.rs:3-8); all data paths (runtime, queries, themes, tests/indent, book/src/generated) are derived from that single anchor (xtask/src/path.rs:10-28).
- CLI contract: first arg selects the task; no arg prints help; an unknown task name returns an `Err` (`Invalid task name`) rather than panicking (xtask/src/main.rs:302-313).

## Key facts

- The crate exists to keep generated docs and language assets in sync with the code: docgen renders the typable-command table, the static-command table (with default keybinds), and the language-support feature matrix straight from helix-term/helix-core registries so the mdbook stays authoritative (xtask/src/docgen.rs:32-191).
- `indent-check` is a regression harness, not a pure validator: under-indent is always a hard failure, but over-indent at a legitimate dedent point is only a counted "note" (gated on under-indents only, because indent-delimited languages cannot know how far to dedent) (xtask/src/main.rs:205-242).
- `indent-check` skips lines it cannot meaningfully assert: commented-out corpus lines (self-documenting edge cases) and `@opaque` interiors (string/comment bodies carrying literal whitespace) are excluded from the typing-indent assertion (xtask/src/main.rs:101-103, 120-125, 168-177).
- `query-check` compiles every grammar's indent/textobject/tag/rainbow tree-sitter queries via `LanguageData`, optionally filtered to a set of `language_id`s, to catch invalid queries before release (xtask/src/main.rs:21-46).
- `theme-check` always includes the two built-in themes `default` and `base16_default` in addition to the on-disk `runtime/themes/` names, and fails if any bundled theme loads with warnings (xtask/src/main.rs:250-280).
- Error handling is uniform `Box<dyn Error>` (`type DynError`) propagated from `main`, with task failures surfaced as process-level `Err` returns (xtask/src/main.rs:7, 302-316).
- Markdown generation escapes `|` to `\|` so command names/keys do not break table columns, and replaces `\n` with `<br>` in command docs (xtask/src/docgen.rs:40, 49, 87).
- `helix-loader` and `toml` are declared dependencies (xtask/Cargo.toml:18, 21) with no direct use in the source; `ropey` is used directly (`ropey::Rope`, xtask/src/main.rs:56) for reading indent-corpus files into a rope.
- Crate inherits all package metadata (version 25.7.1, edition 2021, MPL-2.0 license) from the workspace via `*.workspace = true` (xtask/Cargo.toml:3-9; Cargo.toml:62-70).
<!-- DEEPINIT:END -->
