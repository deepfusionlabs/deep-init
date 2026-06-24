<!--
Provenance:
 stage: EXTRACT (BLIND re-derivation from code only)
 component: helix-stdx
 path: helix-stdx
 inputs: helix-stdx/Cargo.toml, helix-stdx/src/{lib,env,faccess,path,range,rope,uri}.rs, helix-stdx/tests/path.rs, Cargo.toml (workspace)
 date: 2026-06-13
 rule: every claim cites an exact file:line opened inside this component.
-->

# helix-stdx

## Role

- Standard-library extensions: a leaf utility crate of cross-cutting helper functions/types (env, filesystem access, path, range, rope, URI) "used throughout helix" (helix-stdx/src/lib.rs:1-2; helix-stdx/Cargo.toml:3 `description = "Standard library extensions"`).

## Dependencies (edges)

- NO outgoing edges to any other workspace component (helix-core / helix-view / helix-term / helix-tui / helix-lsp-types / helix-lsp / helix-event / helix-dap-types / helix-dap / helix-loader / helix-vcs / helix-parsec / xtask): the manifest's `[dependencies]` lists only third-party crates and contains no `path = "../helix-*"` entry (helix-stdx/Cargo.toml:14-25); a tree-wide grep for `helix_*`/`helix-*` sibling references across this crate's source returns zero hits.
- Depends only on external crates: `dunce` (helix-stdx/Cargo.toml:15), `etcetera` (helix-stdx/Cargo.toml:16), `ropey` (helix-stdx/Cargo.toml:17), `which` (helix-stdx/Cargo.toml:18), `regex-cursor` (helix-stdx/Cargo.toml:19), `bitflags` (helix-stdx/Cargo.toml:20), `once_cell` (helix-stdx/Cargo.toml:21), `regex-automata` (helix-stdx/Cargo.toml:22), `unicode-segmentation` (helix-stdx/Cargo.toml:23), `serde` (helix-stdx/Cargo.toml:24), `percent-encoding` (helix-stdx/Cargo.toml:25).
- Platform-gated external deps: `windows-sys` only on Windows (helix-stdx/Cargo.toml:27-28); `rustix` only on Unix (helix-stdx/Cargo.toml:30-31).
- Confirmed bottom of the workspace DAG: it is a workspace member (Cargo.toml:16) with no intra-workspace dependency edge of its own.

## Data

- Owns one piece of process-global mutable state: the current working directory cached in a `static CWD: RwLock<Option<PathBuf>>` (helix-stdx/src/env.rs:12), kept as a static "so that we can access it in places where we don't have access to the Editor" (helix-stdx/src/env.rs:11), read by `current_working_dir` (helix-stdx/src/env.rs:17-39) and mutated by `set_current_working_dir` (helix-stdx/src/env.rs:42-48).
- Reads host-environment state, not a persistent store: `std::env::var_os` for `PWD` (and `CD` on Windows) in cwd resolution (helix-stdx/src/env.rs:26-28) and for `$VAR` expansion (helix-stdx/src/env.rs:161), plus `std::env::current_dir`/`set_current_dir` (helix-stdx/src/env.rs:24,44).
- Reads filesystem metadata/ACLs for access checks (no writes of app data): Unix `rustix::fs::access` (helix-stdx/src/faccess.rs:59), Windows `GetNamedSecurityInfoW`/`AccessCheck` (helix-stdx/src/faccess.rs:170-183,333-344); `copy_metadata` does write permissions/owner/times onto a destination file (helix-stdx/src/faccess.rs:93,415-445).

## Boundary rules

- Leaf-layer placement: lowest tier of the crate DAG — provides utilities upward but imports no sibling crate (helix-stdx/Cargo.toml:14-25; helix-stdx/src/lib.rs:4-12 declares only its own modules).
- Public surface is the module set re-exported in lib.rs: `env`, `faccess`, `path`, `range`, `rope`, `uri`, plus the flattened re-exports `Range` and `Url` (helix-stdx/src/lib.rs:4-12).
- Cross-platform abstraction boundary in `faccess`: a single public `access`/`copy_metadata`/`hardlink_count` API backed by three `cfg`-selected `imp` modules — unix (helix-stdx/src/faccess.rs:24), windows (helix-stdx/src/faccess.rs:105), and a fallback `cfg(not(any(unix, windows)))` (helix-stdx/src/faccess.rs:464).
- Intra-crate dependency: `path` builds on `env` — `path::canonicalize`/`get_relative_path` call `crate::env::current_working_dir` (helix-stdx/src/path.rs:15,137,152) and `path::expand` calls `crate::env::expand` (helix-stdx/src/path.rs:297); `env::set_current_working_dir` in turn calls `crate::path::canonicalize` (helix-stdx/src/env.rs:43).

## Key facts

- Deliberately ships a hand-rolled minimal RFC3986 `Url` (a newtype over `String`) instead of the `url` crate, because LSP uses RFC3986 (not WHATWG) percent-encoding and some servers (e.g. Deno) reject unescaped `[`/`]` valid under WHATWG but not RFC3986 (helix-stdx/src/uri.rs:1-7,45-46).
- The URI is stored verbatim and path conversion is lazy — only interpreted when a `file://` path is actually needed; serde (de)serialization is opaque/round-trips the raw string (helix-stdx/src/uri.rs:42-46,255-266).
- `path::normalize` normalizes a path WITHOUT resolving symlinks and WITHOUT requiring the path to exist, unlike `std::fs::canonicalize` (helix-stdx/src/path.rs:60-63,130-134); on Windows it has symlink-aware `..` handling that refuses to pop across a symlink (helix-stdx/src/path.rs:83-101).
- `env::expand` implements POSIX-style variable substitution including default-value forms `${VAR:-default}`, `${VAR-default}`, `${VAR:=default}`, `${VAR=default}` via a multi-pattern `regex-automata` meta-Regex and a brace-depth matcher (helix-stdx/src/env.rs:88-162,71-86,154-159).
- `expand_impl` uses `unsafe { OsStr::from_encoded_bytes_unchecked }` / `OsString::from_encoded_bytes_unchecked` justified by codepoint-aligned-substring safety comments — env expansion operates on `OsStr` bytes, not just UTF-8 (helix-stdx/src/env.rs:128-129,149-150).
- `rope::RopeSliceExt` is the central trait extending `ropey::RopeSlice` with regex-input adapters, UTF-8 char-boundary and Unicode grapheme-cluster boundary navigation (`floor/ceil_char_boundary`, `floor/ceil/is_grapheme_boundary`, `nth_next/prev_grapheme_boundary`), with the char-boundary helpers "adapted from std" (helix-stdx/src/rope.rs:13,338,569-574).
- `RopeGraphemes`/`RopeGraphemeIndices` are cursor-like iterators (reversible via `reverse`/`reversed`) rather than `DoubleEndedIterator`, intentionally matching ropey's `Bytes`/`Chars` style (helix-stdx/src/rope.rs:576-580,605-631,710-714).
- `path::find_paths`/`get_path_suffix` detect filesystem paths inside arbitrary text via lazily-compiled, platform-aware regexes built by `compile_path_regex(... cfg!(windows))`, handling URL prefixes, `~`, braced env captures, and Windows `\\?\C:\` / UNC prefixes (helix-stdx/src/path.rs:226-291,213-224).
- `range::Range<T=usize>` is a half-open `[start, end)` range type (`start_bound` Included, `end_bound` Excluded) with `is_subset`/`is_exact_subset` set-containment over sorted, non-overlapping ranges in O(m+n); `is_subset` is const-generic over `ALLOW_EMPTY` (helix-stdx/src/range.rs:6-29,39-48,72-75).
- `faccess` is vendored/derived from the MIT `faccess` crate (helix-stdx/src/faccess.rs:2,9,104,463); on Linux it short-circuits `access` to `Ok` when the process holds ambient `CAP_DAC_OVERRIDE` (helix-stdx/src/faccess.rs:34-39), and on Windows special-cases unmapped Samba users (authority 22) and read-only/extension-based executable checks (helix-stdx/src/faccess.rs:268-315).
- `env::which`/`binary_exists` wrap the `which` crate to locate executables on PATH, surfacing a custom `ExecutableNotFoundError` (helix-stdx/src/env.rs:56-69,164-176).
- The crate is a library only (no `[[bin]]`); it carries unit tests in each module plus a Windows-only integration test for `path::normalize` symlink/case-folding behavior (helix-stdx/tests/path.rs:1 `#![cfg(windows)]`,:12,:41).
