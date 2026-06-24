<!-- DEEPINIT:START -->
# Component: helix-loader

Provenance: stage=EXTRACT (blind, code-only re-derivation) · component=helix-loader · path=helix-loader · inputs=helix-loader/Cargo.toml, helix-loader/build.rs, helix-loader/src/{lib,config,grammar,main,workspace_trust}.rs, Cargo.toml (workspace) · date=2026-06-13

## Role

- Build-bootstrapping crate for the Helix editor: it resolves runtime/config/cache/data directories, loads & merges the `languages.toml` config, and fetches/builds the tree-sitter grammar shared libraries (helix-loader/Cargo.toml:3 `description = "Build bootstrapping for Helix crates"`; helix-loader/src/lib.rs:1-3 modules `config`, `grammar`, `workspace_trust`).

## Dependencies (edges)

- helix-stdx — `use helix_stdx::{env::current_working_dir, path}` and `helix_stdx::env::which("git")` (compile-time path dependency `helix-stdx = { path = "../helix-stdx" }` at helix-loader/Cargo.toml:18; uses at helix-loader/src/lib.rs:5 and helix-loader/src/grammar.rs:87).
- (No other intra-workspace edges.) The only workspace crate it depends on is helix-stdx; all remaining dependencies are external (anyhow, serde, toml, etcetera, once_cell, log, cc, threadpool, tempfile, tree-house) per helix-loader/Cargo.toml:17-34. The grammar ABI type comes from the external `tree-house` crate, not a workspace crate (helix-loader/src/grammar.rs:14 `use tree_house::tree_sitter::Grammar`; helix-loader/Cargo.toml:34 `tree-house.workspace = true`).

## Data

- Runtime grammar libraries / queries directory tree (`runtime/`): grammar `.so`/`.dll`/`.dylib`/`.wasm` files under `runtime/grammars/<name>` and query files under `runtime/queries/<lang>/<file>` are read and written here (helix-loader/src/grammar.rs:16-26 DYLIB_EXTENSION by OS;:75-77 `grammars/<name>` lookup;:718-721 `queries/<language>/<filename>` read).
- Vendored grammar git sources: each grammar is cloned into `<runtime>/grammars/sources/<grammar_id>` as a git repo (helix-loader/src/grammar.rs:338-345 VendoredGrammar dir;:369-390 init/`git init`;:357-364 fetch/checkout).
- Config file `config.toml` and language config `languages.toml`: global at config_dir, workspace at `.helix/`, plus a compile-time-embedded default `languages.toml` via `include_bytes!("../../languages.toml")` (helix-loader/src/lib.rs:151-161; helix-loader/src/config.rs:6-9,:13-34).
- Log file `helix.log` under cache_dir (helix-loader/src/lib.rs:163-165).
- Workspace-trust store: plaintext newline-delimited path lists `trusted_workspaces` and `excluded_workspaces` under data_dir (helix-loader/src/lib.rs:167-173; helix-loader/src/workspace_trust.rs:31-62 read;:65-103 write).

## Boundary rules

- Trust gate on config merge: user/workspace `languages.toml` is only merged in when the workspace is Trusted (or `insecure==true`); an untrusted workspace gets only the global config (helix-loader/src/config.rs:13-21 `quick_query_workspace`; helix-loader/src/workspace_trust.rs:142-159).
- Runtime-dir priority order is a fixed 5-level precedence (CARGO_MANIFEST_DIR sibling → user config subdir → `HELIX_RUNTIME` → build-time `HELIX_DEFAULT_RUNTIME` → exe-sibling), documented as a postcondition of ≥2 paths (helix-loader/src/lib.rs:31-78).
- Global static initialization: `RUNTIME_DIRS` is a `Lazy<Vec<PathBuf>>` computed once; `CONFIG_FILE` / `LOG_FILE` are write-once `OnceCell`s set via `initialize_*` and read via accessors that `unwrap` (helix-loader/src/lib.rs:12-29,:143-149).

## Key facts

- The `hx-loader` binary (src/main.rs) exists only as a Release-CI optimization to pre-fetch grammars with STRICT=true and is explicitly "not meant to be run manually" (helix-loader/Cargo.toml:13-15; helix-loader/src/main.rs:4-11).
- `build.rs` injects `VERSION_AND_GIT_HASH` (CalVer + 8-char git hash) and `BUILD_TARGET` as compile-time env vars, and emits `rerun-if-changed` on git HEAD so version rebuilds; falls back to `HELIX_NIX_BUILD_REV` (helix-loader/build.rs:5-39,:60-81; consumed at helix-loader/src/lib.rs:10 and helix-loader/src/grammar.rs:65).
- Grammars are fetched as shallow (`--depth 1`) git checkouts; a grammar dir is force-removed and re-inited before each fetch for clean state, and `extract_object_format_from_revision` auto-detects sha1 vs sha256 (64-hex or explicit prefix) for `git init --object-format` (helix-loader/src/grammar.rs:357-364,:393-397,:316-330,:369-382).
- Grammar build compiles tree-sitter `parser.c` (C11) + optional `scanner.c`/`scanner.cc` (C++14) into a shared lib via the `cc` crate, MSVC vs GCC/Clang branches, with `-fno-exceptions`, `-fPIC` (non-windows), and RELRO/now hardening on Linux; recompile is mtime-gated (helix-loader/src/grammar.rs:508-690,:670-675,:692-710).
- Grammar fetching/building runs in parallel over a `threadpool` with results funneled through an mpsc `channel`; SendErrors are intentionally ignored on early receiver close (helix-loader/src/grammar.rs:271-293).
- `merge_toml_values` is a name-keyed recursive TOML merge with a `merge_depth` cutoff, used to layer user config over the embedded default `languages.toml` (helix-loader/src/lib.rs:175-256; helix-loader/src/config.rs:31-34 fold at depth 3).
- `find_workspace` walks CWD ancestors and treats the first dir containing `.git`/`.svn`/`.jj`/`.helix` as the workspace root, else `(CWD, true)` (helix-loader/src/lib.rs:265-283).
- Base directory resolution (config/cache/data) is delegated to the `etcetera` crate's `choose_base_strategy`, with TODOs noting env-var overrides are not yet supported (helix-loader/src/lib.rs:120-141).
<!-- DEEPINIT:END -->
