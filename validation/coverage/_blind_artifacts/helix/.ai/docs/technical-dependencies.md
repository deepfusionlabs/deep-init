<!--
Provenance
- stage: blind-mirror-test (DeepInit EMIT/GENERATE)
- repo: helix@blind
- doc_in_inputs: false
- run: P5 Mirror-Test blind artifact
- date: 2026-06-13
- inputs: source files + Cargo manifests + directory layout only (architecture/design prose docs removed from tree)
-->

# Technical dependencies (full edge list)

Each edge is grounded to the file:line where it was observed. The workspace dependency graph is a strict acyclic DAG (Cargo bans cross-crate dependency cycles, Cargo.toml:1-18); helix-stdx is the bottom and helix-term/xtask the top.

## helix-core

- helix-core -> helix-stdx — project-ref (Cargo path dep) + import — helix-core/Cargo.toml:19; helix-core/src/indent.rs:6; helix-core/src/uri.rs:56
- helix-core -> helix-loader — project-ref (Cargo path dep) + import — helix-core/Cargo.toml:20; helix-core/src/syntax.rs:17; helix-core/src/config.rs:8; helix-core/src/lib.rs:43
- helix-core -> helix-parsec — project-ref (Cargo path dep) + import — helix-core/Cargo.toml:21; helix-core/src/snippets/parser.rs:29

Boundary note: helix-core depends ONLY on helix-stdx/helix-loader/helix-parsec (helix-core/Cargo.toml:19-21) and references no higher-level helix crate anywhere in src — a tree-wide search found zero refs to helix-view/term/tui/lsp/event/dap/vcs/xtask.

## helix-view

- helix-view -> helix-core — import / project-ref — helix-view/Cargo.toml:20; helix-view/src/editor.rs:46-54; helix-view/src/lib.rs:85
- helix-view -> helix-event — queue-event / project-ref — helix-view/Cargo.toml:21; helix-view/src/events.rs:2,7; helix-view/src/editor.rs:17,2046,2142
- helix-view -> helix-loader — import / project-ref — helix-view/Cargo.toml:22; helix-view/src/theme.rs:9; helix-view/src/editor.rs:18,1746; helix-view/src/expansion.rs:286
- helix-view -> helix-lsp — import / runtime-call — helix-view/Cargo.toml:23; helix-view/src/editor.rs:23,56,1208; helix-view/src/document.rs:16
- helix-view -> helix-dap — import / runtime-call — helix-view/Cargo.toml:24; helix-view/src/editor.rs:55,1212,1271
- helix-view -> helix-vcs — import / project-ref — helix-view/Cargo.toml:25; helix-view/src/editor.rs:19,1210; helix-view/src/document.rs:18
- helix-view -> helix-stdx — import / project-ref — helix-view/Cargo.toml:19; helix-view/src/editor.rs:57,501,524; helix-view/src/document.rs:17; helix-view/src/clipboard.rs:108,119,135
- helix-view -> helix-tui — dev-dependency-only (no runtime edge; doctest-only refs) — helix-view/Cargo.toml:65; helix-view/src/graphics.rs:537,565

Boundary note: helix-view has no direct edges to helix-term, helix-lsp-types, helix-dap-types, helix-parsec, or xtask — not in Cargo.toml and no source refs; wire types are reached transitively via helix-lsp/helix-dap (helix-view/Cargo.toml:18-65).

## helix-term

- helix-term -> helix-core — import — helix-term/src/commands.rs:22-46
- helix-term -> helix-view — import (macro_use extern crate + types) — helix-term/src/lib.rs:1-2
- helix-term -> helix-lsp — import (LSP client + lsp:: protocol types) — helix-term/src/application.rs:4-8
- helix-term -> helix-dap — import (DAP client + dap:: protocol types) — helix-term/src/commands/dap.rs:7-9
- helix-term -> helix-vcs — import (feature-gated by default `git`) — helix-term/src/commands.rs:13
- helix-term -> helix-loader — import + build-dependency (grammar/config/runtime) — helix-term/Cargo.toml:99-100
- helix-term -> helix-event — import (event/hook system, redraw, runtime_local) — helix-term/src/handlers.rs:5
- helix-term -> helix-stdx — import (path/env/rope/Url helpers) — helix-term/src/application.rs:9
- helix-term -> helix-tui — import (renamed package `tui`: backends, Terminal, Surface) — helix-term/Cargo.toml:57

Boundary note: helix-term has no direct edge to helix-lsp-types (reached via helix-lsp lsp::), helix-dap-types (via helix-dap dap::), helix-parsec, or xtask — none appear in [dependencies] (helix-term/Cargo.toml:44-51).

## helix-tui

- helix-tui -> helix-view — project-ref (path dep, feature=term) — helix-tui/Cargo.toml:18
- helix-tui -> helix-view — import (graphics::{Rect,Style,Color,Modifier,UnderlineStyle,CursorKind}, editor::Config, theme::Mode) — helix-tui/src/backend/mod.rs:7
- helix-tui -> helix-view — import (graphics + editor::Config conversion) — helix-tui/src/terminal.rs:5
- helix-tui -> helix-core — project-ref (path dep) — helix-tui/Cargo.toml:19
- helix-tui -> helix-core — import (unicode::width::{UnicodeWidthChar,UnicodeWidthStr}) — helix-tui/src/buffer.rs:3
- helix-tui -> helix-core — import (line_ending::str_is_line_ending, unicode::width) — helix-tui/src/text.rs:49

Boundary note: helix-tui has no code dependency on any helix crate other than helix-view and helix-core — a full grep of helix-tui/src for helix_* yields only those two (plus helix_tui self-references in doctests) (helix-tui/Cargo.toml:17).

## helix-lsp

- helix-lsp -> helix-lsp-types — import (path dep, re-exported as `lsp`) — helix-lsp/src/lib.rs:10
- helix-lsp -> helix-core — import (Rope/ChangeSet/Selection/Transaction, syntax config, LanguageServerId, diff::compare_ropes) — helix-lsp/src/lib.rs:16
- helix-lsp -> helix-stdx — runtime-call (env::which to resolve the server binary, path normalize, cwd) — helix-lsp/src/client.rs:226
- helix-lsp -> helix-loader — runtime-call (find_workspace) + import (VERSION_AND_GIT_HASH) — helix-lsp/src/lib.rs:904

Boundary note: helix-lsp's only path deps are helix-stdx/helix-core/helix-loader/helix-lsp-types (helix-lsp/Cargo.toml:15-19) — no edge to helix-view/term/tui/event/dap/vcs/parsec (the lone helix_view mention is a doc comment, helix-lsp/src/lib.rs:652).

## helix-dap

- helix-dap -> helix-dap-types — import (path-dep, glob re-export) — helix-dap/Cargo.toml:18; helix-dap/src/lib.rs:6
- helix-dap -> helix-dap-types — runtime-call (Request trait bound on every RPC) — helix-dap/src/client.rs:254
- helix-dap -> helix-core — import (path-dep; uses syntax::config::DebugAdapterConfig, DebuggerQuirks) — helix-dap/Cargo.toml:17; helix-dap/src/client.rs:7
- helix-dap -> helix-stdx — import (path-dep; env::which binary resolution + ExecutableNotFoundError) — helix-dap/Cargo.toml:16; helix-dap/src/client.rs:120

## helix-loader

- helix-loader -> helix-stdx — import (use helix_stdx::{env::current_working_dir, path}) — helix-loader/src/lib.rs:5
- helix-loader -> helix-stdx — runtime-call (helix_stdx::env::which("git")) — helix-loader/src/grammar.rs:87
- helix-loader -> helix-stdx — project-ref (helix-stdx = { path = "../helix-stdx" }) — helix-loader/Cargo.toml:18

Boundary note: helix-loader's only intra-workspace dependency is helix-stdx; all other deps are external crates (helix-loader/Cargo.toml:17-34).

## helix-lsp-types

- helix-lsp-types -> helix-stdx — project-ref (Cargo path dependency) — helix-lsp-types/Cargo.toml:27
- helix-lsp-types -> helix-stdx — import (re-export of the Url type) — helix-lsp-types/src/lib.rs:24

Boundary note: its only sibling edge is../helix-stdx (helix-lsp-types/Cargo.toml:27); it imports no other workspace component (NONE found in a full source+manifest scan), so it sits at the bottom of the acyclic graph with no cycle possible.

## helix-vcs

- helix-vcs -> helix-core — import (uses Rope/RopeSlice as the diffed text type) — helix-vcs/src/diff.rs:4; helix-vcs/Cargo.toml:13
- helix-vcs -> helix-event — runtime-call (lock_frame + request_redraw, RenderLockGuard) — helix-vcs/src/diff.rs:86; helix-vcs/src/worker.rs:169,195; helix-vcs/src/diff.rs:5; helix-vcs/Cargo.toml:14

## xtask

- xtask -> helix-term — import+runtime-call (TYPABLE_COMMAND_LIST, MappableCommand::STATIC_COMMAND_LIST, health::TsFeature, keymap::default) — xtask/src/docgen.rs:5-7,59,72; xtask/Cargo.toml:15
- xtask -> helix-core — import+runtime-call (config::default_lang_loader/default_lang_config, LanguageData, indent::*, Syntax) — xtask/src/main.rs:22-40,49-59; xtask/src/docgen.rs:133; xtask/Cargo.toml:16
- xtask -> helix-view — import+runtime-call (document::Mode, theme::Loader::{new,read_names,load_with_warnings}) — xtask/src/docgen.rs:8,62-64; xtask/src/main.rs:246-263; xtask/Cargo.toml:17
- xtask -> helix-stdx — import+runtime-call (RopeSliceExt::first_non_whitespace_char) — xtask/src/main.rs:55,115,163; xtask/Cargo.toml:19
- xtask -> helix-loader — manifest-dep-only (no direct source use) — xtask/Cargo.toml:18 (declared; no helix_loader:: reference in xtask/src/*.rs)
- xtask (internal-module-wiring) — mod docgen/helpers/path — xtask/src/main.rs:1-3; xtask/src/docgen.rs:1-2; xtask/src/helpers.rs:3

Boundary note: xtask is a top-of-graph consumer; nothing depends back on it (absent from other crates' deps and from default-members, Cargo.toml:20-22), so it introduces no cycle.

## Leaf crates (no outgoing intra-workspace edges)

- helix-event — manifest [dependencies] are all external crates; source has no `use helix_*` reference — helix-event/Cargo.toml:14-26; helix-event/src/lib.rs:26,30,32
- helix-dap-types — manifest [dependencies] lists only third-party serde/serde_json; no helix-* path/workspace dep — helix-dap-types/Cargo.toml:13-15
- helix-parsec — empty [dependencies]; lib.rs has no `use`/`extern crate`/`helix_*` reference — helix-parsec/Cargo.toml:14; helix-parsec/src/lib.rs:1-575
- helix-stdx — bottom of the DAG; [dependencies] contain no `path = "../helix-*"` entry — helix-stdx/Cargo.toml:14-25
