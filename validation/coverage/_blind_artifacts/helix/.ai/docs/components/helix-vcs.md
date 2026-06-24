<!-- DEEPINIT:START -->
<!--
Provenance:
 stage: EXTRACT (blind, code-only re-derivation)
 component: helix-vcs
 path: helix-vcs
 run: p5-mirror-blind
 inputs: helix-vcs/Cargo.toml, helix-vcs/src/{lib,diff,status,git}.rs,
 helix-vcs/src/diff/{line_cache,worker}.rs, helix-vcs/src/diff/worker/test.rs,
 helix-term/Cargo.toml (feature-gate evidence)
 date: 2026-06-13
-->

# helix-vcs

## Role

- Provides types for working with diffs from a Version Control System; `git` is the only currently-supported diff provider, but the architecture is built to allow other providers later. (helix-vcs/src/lib.rs:1)
- Owns the live, asynchronously-recomputed line diff between a base text and an editing document, plus VCS file-status enumeration. (helix-vcs/src/diff.rs:38, helix-vcs/src/status.rs:3)

## Dependencies (edges)

- **helix-core** — uses `Rope` / `RopeSlice` as the text representation that is diffed. (helix-vcs/src/diff.rs:4; helix-vcs/src/diff/worker.rs:3; helix-vcs/src/diff/line_cache.rs:15)
- **helix-core** — declared as a path dependency in the manifest. (helix-vcs/Cargo.toml:13)
- **helix-event** — calls `lock_frame` to acquire a render lock, holds a `RenderLockGuard`, and calls `request_redraw` to trigger a redraw after a diff completes. (helix-vcs/src/diff.rs:5; helix-vcs/src/diff.rs:86; helix-vcs/src/diff/worker.rs:169; helix-vcs/src/diff/worker.rs:195)
- **helix-event** — declared as a path dependency in the manifest. (helix-vcs/Cargo.toml:14)
- No outgoing edges to helix-view, helix-term, helix-tui, helix-lsp(-types), helix-dap(-types), helix-loader, helix-parsec, helix-stdx, or xtask were found; only helix-core and helix-event are referenced in source and in the manifest. (helix-vcs/Cargo.toml:13)
- **Reverse edge (inbound, for context):** helix-term gates this crate behind its own `git` feature: `git = ["helix-vcs/git"]`, with `helix-vcs = { path = "../helix-vcs" }`. (helix-term/Cargo.toml:37; helix-term/Cargo.toml:50)
- External crates: `gix` (git plumbing, optional, gates the `git` feature), `imara-diff` (diff algorithm + `Hunk`), `tokio` (async runtime / channels / blocking tasks), `arc-swap`, `parking_lot`, `anyhow`, `log`. (helix-vcs/Cargo.toml:16-24)

## Data

- Reads from the on-disk **git repository** via `gix`: opens/discovers a repo upward from the file's parent directory, reads the HEAD commit's blob for a file as the "diff base", reads the current HEAD ref/short-hash name, and enumerates working-tree status. It is read-only against git object/worktree state — no writes. (helix-vcs/src/git.rs:30; helix-vcs/src/git.rs:62; helix-vcs/src/git.rs:82; helix-vcs/src/git.rs:119)
- In-memory diff state store: `DiffInner { diff_base: Rope, doc: Rope, hunks: Vec<Hunk> }` held behind `Arc<RwLock<...>>`, written by the worker and read via a `DiffHandle`. (helix-vcs/src/diff.rs:31; helix-vcs/src/diff.rs:40; helix-vcs/src/diff/worker.rs:72)
- Reused line-interning cache `InternedRopeLines` keeps the base/doc lines interned to avoid reallocating per diff. (helix-vcs/src/diff/line_cache.rs:22)

## Boundary rules

- **Feature-gated provider boundary:** the git provider module is compiled only under `#[cfg(feature = "git")]`; without it, `DiffProvider::None` returns `bail!("No diff support compiled in")`. (helix-vcs/src/lib.rs:12; helix-vcs/src/lib.rs:109)
- **Provider registry indirection:** all VCS access goes through `DiffProviderRegistry`, which iterates providers and swallows per-provider errors into `log::debug!` + `None`, so callers get an `Option`, never a hard failure, when reading a diff base / head name. (helix-vcs/src/lib.rs:33; helix-vcs/src/lib.rs:39)
- **Render-loop discipline:** `update_document` is documented as "only intended to be called from within the rendering loop"; it acquires a render lock and may panic if called elsewhere. (helix-vcs/src/diff.rs:83)
- **Off-the-async-runtime compute:** the actual diff computation is moved off the async executor via `tokio::task::block_in_place` (except under `#[cfg(test)]`, where it runs inline) because diffing is CPU-expensive and must not block other futures. (helix-vcs/src/diff/worker.rs:57; helix-vcs/src/diff/worker.rs:60)
- **Background status iteration:** `for_each_changed_file` runs the whole walk inside `tokio::task::spawn_blocking` and is fire-and-forget; iteration stops when the callback returns `false`. (helix-vcs/src/lib.rs:60; helix-vcs/src/lib.rs:67)
- **DB/repo safety:** `get_diff_base` / `get_current_head_name` assert the input path is absolute and (if it exists) is a file, and resolve symlinks via `gix::path::realpath` before touching the repo. (helix-vcs/src/git.rs:31; helix-vcs/src/git.rs:33)

## Key facts

- **Trait-object workaround:** `DiffProvider` is a `#[derive(Copy, Clone)] enum` (Git | None) rather than a `dyn DiffProvider`, explicitly to let `DiffProviderRegistry` derive `Clone` — the comment notes `Clone` cannot be used in trait objects. (helix-vcs/src/lib.rs:93; helix-vcs/src/lib.rs:97)
- **Default registry composition:** the default registry is `[Git (if feature on), None]`, with a TODO to make providers configurable once more exist. (helix-vcs/src/lib.rs:82; helix-vcs/src/lib.rs:88)
- **Diff algorithm choice:** the histogram algorithm is hard-coded (`ALGORITHM = Algorithm::Histogram`) and postprocessed with an indent heuristic (tab width 4). (helix-vcs/src/diff.rs:121; helix-vcs/src/diff/worker.rs:90)
- **Diff-size cap:** diffs are skipped (returns `None`) when a side exceeds `MAX_DIFF_LINES = 64 * u16::MAX` lines or `MAX_DIFF_BYTES = MAX_DIFF_LINES * 128` bytes, bounding both line count and total bytes. (helix-vcs/src/diff.rs:122; helix-vcs/src/diff.rs:124; helix-vcs/src/diff/line_cache.rs:116)
- **Debounce tuning:** synchronous (render-blocking) updates use a 1 ms debounce and a 12 ms render-block timeout; async updates use a 96 ms debounce. (helix-vcs/src/diff.rs:117; helix-vcs/src/diff.rs:119; helix-vcs/src/diff.rs:120)
- **Invertible diff:** a `DiffHandle` carries an `inverted` flag that swaps the base/doc roles (and inverts hunks) on read, used to view the diff from either direction. (helix-vcs/src/diff.rs:43; helix-vcs/src/diff.rs:70; helix-vcs/src/diff.rs:159)
- **Hunk navigation by binary search:** `next_hunk` / `prev_hunk` / `hunk_at` binary-search the sorted, non-overlapping hunk list, with explicit handling of pure-removal (empty-range) hunks. (helix-vcs/src/diff.rs:176; helix-vcs/src/diff.rs:203; helix-vcs/src/diff.rs:247)
- **Self-referential cache via `unsafe transmute`:** `InternedRopeLines` transmutes `RopeSlice` lifetimes to `'static` so the lines-vec can be reused across diffs against the boxed rope it owns; safety relies on the interner being cleared before the backing rope is replaced. (helix-vcs/src/diff/line_cache.rs:11; helix-vcs/src/diff/line_cache.rs:85; helix-vcs/src/diff/line_cache.rs:102)
- **Incremental re-intern optimization:** `update_doc` re-interns only the doc (erasing tokens added after the base) and is documented as significantly faster than `update_diff_base`, which re-interns both. (helix-vcs/src/diff/line_cache.rs:55; helix-vcs/src/diff/line_cache.rs:68)
- **Head name as shared swappable string:** `get_current_head_name` returns `Arc<ArcSwap<Box<str>>>` (branch short-name, or 8-char short hash when detached), so the displayed HEAD name can be atomically swapped under readers. (helix-vcs/src/git.rs:62; helix-vcs/src/git.rs:74)
- **git-status emulation:** `status` emulates `git status` — forces untracked-files listing (overriding `status.showUntrackedFiles`), turns on rename detection (50% similarity, limit 1000), and maps `intent-to-add` files to `Untracked` (noting Jujutsu marks new files this way). (helix-vcs/src/git.rs:128; helix-vcs/src/git.rs:141; helix-vcs/src/git.rs:143; helix-vcs/src/git.rs:176)
- **Windows-specific config lookup:** repo open permissions enable `git_binary` config discovery only on Windows (`cfg!(windows)`), because that path lookup has overhead and is not gitoxide's default. (helix-vcs/src/git.rs:94; helix-vcs/src/git.rs:100)
- **diff-base filter pipeline:** the diff base blob is passed through gix's filter pipeline (`convert_to_worktree`) so user git config / attributes (e.g. CRLF conversion) are applied, matching what git would materialize. (helix-vcs/src/git.rs:48; helix-vcs/src/git.rs:51)
- **FileChange taxonomy:** working-tree changes are modeled as `Untracked | Modified | Conflict | Deleted | Renamed{from,to}`, with `path` returning the destination path for renames. (helix-vcs/src/status.rs:3; helix-vcs/src/status.rs:21)
<!-- DEEPINIT:END -->
