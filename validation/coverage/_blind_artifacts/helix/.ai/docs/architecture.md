<!--
Provenance
- stage: blind-mirror-test (DeepInit EMIT/GENERATE)
- repo: helix@blind
- doc_in_inputs: false
- run: P5 Mirror-Test blind artifact
- date: 2026-06-13
- inputs: source files + Cargo manifests + directory layout only (architecture/design prose docs removed from tree)
-->

# Architecture overview

Helix is a modal terminal text editor built as a single Cargo workspace (Cargo.toml:1-18, resolver "2") of 14 layered crates whose dependency graph is a strict DAG (Cargo bans cross-crate dependency cycles). The shipped binary is `hx`, produced by the lone default-member helix-term (Cargo.toml:20-22; helix-term/Cargo.toml:39-40), which runs on a multi-threaded Tokio async runtime (helix-term/src/main.rs:25 `#[tokio::main]`) and renders through a stacked-layer Compositor of `dyn Component` widgets (helix-term/src/compositor.rs:78-79). The data foundation is helix-core, which re-exports the ropey rope buffer as the text model (helix-core/src/lib.rs:48) and embeds a tree-sitter syntax engine (helix-core/src/syntax.rs); editor state is centralized in helix-view's Editor struct, holding Documents and Views in slotmap/BTreeMap registries keyed by DocumentId/ViewId (helix-view/src/editor.rs:1190-1199). Language tooling is split into client crates (helix-lsp for LSP, helix-dap for DAP), each over its own JSON-RPC transport (helix-lsp/src/jsonrpc.rs, helix-lsp/src/transport.rs:43) and paired with a pure protocol-types crate (helix-lsp-types, helix-dap-types). Cross-cutting concerns are factored into small leaf crates: helix-event (synchronous hook dispatch, helix-event/src/lib.rs:84), helix-loader (runtime-dir resolution + tree-sitter grammar build/fetch, helix-loader/src/lib.rs:2,38), helix-vcs (git integration), helix-tui (terminal rendering over termina/crossterm, helix-tui/Cargo.toml:15), plus the dependency-free helix-stdx and helix-parsec. The crate layering bottoms out at helix-stdx (no intra-workspace deps) and tops out at helix-term/xtask.

## Component decomposition rationale (grounded)

The system is decomposed into crates that are also the workspace members declared in the root manifest [workspace].members list (Cargo.toml:4-17). The decomposition follows the dependency DAG strictly bottom-to-top:

### Foundation / leaf crates (no intra-workspace dependencies)

- **helix-stdx** — the bottom of the workspace crate DAG; a workspace member (Cargo.toml:16) whose [dependencies] contain no `path = "../helix-*"` entry, so it imports no sibling crate (helix-stdx/Cargo.toml:14-25). It provides cross-cutting standard-library extensions (env, faccess, path, range, rope, uri) used throughout helix (helix-stdx/src/lib.rs:1-2). Bottom-of-graph placement is what lets nearly every other crate depend on it.
- **helix-parsec** — a self-contained parser-combinator library (helix-parsec/Cargo.toml:3) with an empty [dependencies] section and no `use`/`extern crate`/`helix_*` reference anywhere in source, i.e. ZERO outgoing dependency edges — a true leaf (helix-parsec/Cargo.toml:14; helix-parsec/src/lib.rs:1-575). It can only be consumed, never reach back into another component.
- **helix-event** — a decoupling layer for component-to-component communication without strong coupling (helix-event/src/lib.rs:1-5). Its manifest [dependencies] are all external crates with NO helix-* member and its source has no `use helix_*` reference, making it a foundational/leaf crate in the DAG (helix-event/Cargo.toml:14-26; helix-event/src/lib.rs:26,30,32).
- **helix-lsp-types** / **helix-dap-types** — pure data-type crates for the LSP (helix-lsp-types/Cargo.toml:12) and DAP (helix-dap-types/src/lib.rs:6-9) wire protocols. helix-dap-types has no sibling-crate dependency at all (helix-dap-types/Cargo.toml:13-15); helix-lsp-types has a single sibling edge to../helix-stdx for the Url type and no other (helix-lsp-types/Cargo.toml:27; helix-lsp-types/src/lib.rs:24). Separating protocol *types* from protocol *behavior* keeps the type crates at the bottom of the acyclic graph so no cycle is possible.

### Core / mid-layer crates

- **helix-core** — the editor's text-editing core library: it owns the document buffer (Rope), selections, atomic edit transactions (ChangeSet), undo history, and the tree-sitter-backed syntax engine, with no terminal/UI concerns (helix-core/Cargo.toml:3; helix-core/src/lib.rs:48; helix-core/src/syntax.rs:514). It depends ONLY on helix-stdx/helix-loader/helix-parsec (helix-core/Cargo.toml:19-21) and references no higher-level helix crate in its source, confirming the layering direction.
- **helix-loader** — build-bootstrapping: it resolves runtime/config/cache/data directories, merges languages.toml, and fetches/builds the tree-sitter grammar shared libraries (helix-loader/Cargo.toml:3; helix-loader/src/lib.rs:1-3). Its only intra-workspace dependency is helix-stdx (helix-loader/Cargo.toml:17-34). It also ships the hx-loader binary as a Release-CI grammar-prefetch optimization, not for manual use (helix-loader/Cargo.toml:13-15; helix-loader/src/main.rs:4-11).
- **helix-vcs** — VCS-diff types owning the live, asynchronously-recomputed line diff between a base text and the editing document, plus git working-tree status (helix-vcs/src/lib.rs:1). It depends on helix-core (for the Rope text type) and helix-event (for render-loop coordination) (helix-vcs/Cargo.toml:13-14). It is gated by the `git` feature, which helix-term enables via `git = ["helix-vcs/git"]` (helix-term/Cargo.toml:37).

### View / state layer

- **helix-view** — provides the editor-state model and UI abstractions for backends, owning the central Editor struct that holds the Document/View registries plus mode, registers, theme, diagnostics, and handler wiring (helix-view/src/editor.rs:1190-1262; helix-view/Cargo.toml:3). It depends on helix-core/helix-event/helix-loader/helix-lsp/helix-dap/helix-vcs/helix-stdx, sitting above the core+client layer (helix-view/Cargo.toml:18-65). It is a library crate with no binary (helix-view/src/lib.rs:1-19). Handler implementations live upstream in helix-term, which is why the Handlers fields are public (helix-view/src/handlers.rs:20-30).

### Client crates (protocol behavior)

- **helix-lsp** — the LSP client library: it spawns each language server as a child process and speaks JSON-RPC 2.0 over stdio, exposing typed methods via Client (helix-lsp/Cargo.toml:3; helix-lsp/src/lib.rs:8). It is the boundary that converts editor-side helix_core types to/from wire-side lsp types (helix-lsp/src/lib.rs:90,146,223). Its only path deps are helix-stdx/helix-core/helix-loader/helix-lsp-types (helix-lsp/Cargo.toml:15-19).
- **helix-dap** — the DAP client library: it spawns a debug-adapter process, speaks DAP over stdio or TCP, and exposes typed request/event/registry APIs (helix-dap/Cargo.toml:3; helix-dap/src/client.rs:30). It depends on helix-dap-types/helix-core/helix-stdx (helix-dap/Cargo.toml:16-18).

### Rendering layer

- **helix-tui** — an immediate-mode terminal-UI rendering library: a double-buffered cell grid (`Buffer` of `Cell`s) behind a swappable `Backend` trait, a Cassowary constraint-solver layout engine, a styled-text model, and drawable widgets that emit only the minimal diff of changed cells per frame (helix-tui/Cargo.toml:3; helix-tui/src/lib.rs:1). It depends only on helix-view and helix-core (helix-tui/Cargo.toml:17-19); the helix-view edge is feature-gated by `term` (helix-tui/Cargo.toml:18).

### Application / top of graph

- **helix-term** — the application/binary crate producing the `hx` executable and the top-level orchestrator: its `#[tokio::main]` entry constructs and runs Application, which owns the run loop, the Compositor UI layer stack, the Terminal backend, the Editor state, the job queue, and the LSP progress map (helix-term/src/application.rs:70-82). It is the sole default-member (Cargo.toml:6,21) and depends on every other shipped crate (helix-term/Cargo.toml).
- **xtask** — a developer-tooling/automation binary (cargo-xtask pattern) running workspace maintenance tasks (docgen, query-check, indent-check, theme-check), not part of the shipped editor (xtask/src/main.rs:302-316). It is listed last in [workspace].members and is separate from default-members=[helix-term], so it is built only when explicitly targeted (Cargo.toml:3-22); nothing depends back on it, introducing no cycle.

## Layering invariant

The crate layering is acyclic and directional: helix-stdx (no intra-workspace deps, helix-stdx/Cargo.toml:14-25) at the bottom, then the leaf protocol-types/event/parsec crates, then helix-core/helix-loader, then the client crates and helix-view, then helix-tui, and finally helix-term and xtask at the top. Cargo's cross-crate dependency-cycle ban makes any intra-workspace import cycle structurally impossible (Cargo.toml:1-18), and several crates verify their leaf/bottom status by source-wide search showing no sibling `use helix_*` reference (e.g. helix-event/src/lib.rs:26,30,32; helix-parsec/src/lib.rs:1-575; helix-dap-types/Cargo.toml:13-15).
