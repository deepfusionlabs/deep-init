<!-- DEEPINIT:START -->
<!--
provenance:
 stage: EXTRACT (BLIND re-derivation from code only — prose docs removed from tree)
 component: helix-lsp-types
 path: helix-lsp-types
 inputs: helix-lsp-types/Cargo.toml, helix-lsp-types/src/*.rs
 rule: R1 (cite file:line; omit over speculate)
-->

# Component: helix-lsp-types

## Role

- A pure, dependency-light Rust *data-type* library crate (`name = "helix-lsp-types"`, a `[package]` with no binary target) that models VSCode's Language Server Protocol message types for Rust — `description = "Types for interaction with a language server, using VSCode's Language Server Protocol"` (helix-lsp-types/Cargo.toml:2, helix-lsp-types/Cargo.toml:12).
- Its crate-doc states the responsibility directly: "Language Server Protocol types for Rust. Based on the LSP specification" (helix-lsp-types/src/lib.rs:3-5). It is a fork of `gluon-lang/lsp-types` (helix-lsp-types/Cargo.toml:14).

## Dependencies (edges)

- → **helix-stdx** (the ONLY outgoing edge to a sibling workspace component): manifest path dependency `helix-stdx = { path = "../helix-stdx" }` (helix-lsp-types/Cargo.toml:27), consumed as a single re-exported type `pub use helix_stdx::Url;` (helix-lsp-types/src/lib.rs:24). `Url` is then used pervasively for LSP location fields, e.g. `pub uri: Url` (helix-lsp-types/src/lib.rs:280) and `pub target_uri: Url` (helix-lsp-types/src/lib.rs:302).
- No edges to any other workspace component — a full source+manifest scan for `helix_core / helix_view / helix_term / helix_tui / helix_lsp / helix_event / helix_dap* / helix_loader / helix_vcs / helix_parsec / xtask` found NONE (verified: only `crate::`-internal references plus external crates remain; helix-lsp-types/Cargo.toml:23-27).
- External (non-component) crate deps, for completeness: `bitflags.workspace = true`, `serde` 1.0.228 with `derive`, `serde_json` 1.0.150 (helix-lsp-types/Cargo.toml:24-26); used as `use bitflags::bitflags;` (helix-lsp-types/src/lib.rs:20) and `use serde::{...Deserialize, Serialize}; use serde_json::Value;` (helix-lsp-types/src/lib.rs:25-26).

## Data

- Owns NO runtime persistence / data-store. The crate is purely declarative serde-(de)serializable structs/enums — its "data" is the on-the-wire JSON-RPC payload schema, not a database. Type aliases bind the LSP "any" types straight to serde_json: `pub type LSPAny = serde_json::Value;`, `pub type LSPObject = serde_json::Map<String, serde_json::Value>;`, `pub type LSPArray = Vec<serde_json::Value>;` (helix-lsp-types/src/lib.rs:227-237).

## Boundary rules

- Hard safety boundary: `#![forbid(unsafe_code)]` — the entire crate is compile-time forbidden from using `unsafe` (helix-lsp-types/src/lib.rs:18).
- Strong layering position: a leaf data crate that depends on exactly one sibling (helix-stdx) and is depended-upon-by the LSP-client layer (no inbound knowledge encoded here). It participates in Cargo's cross-crate acyclic-dependency rule — its sole sibling edge `../helix-stdx` (helix-lsp-types/Cargo.toml:27) keeps it at the bottom of the dependency DAG (no cycle possible: it imports no other component).
- Stability boundary: an opt-in `proposed` Cargo feature carves unstable LSP extensions out of the default API surface — `default = []`, `proposed = []` with the comment "No semver compatibility is guaranteed for types enabled by this feature" (helix-lsp-types/Cargo.toml:29-33); enforced in source by 10 `#[cfg(feature = "proposed")]` gates (e.g. the entire `inline_completion` module, helix-lsp-types/src/lib.rs:156-159).
- Module-surface convention: every domain module is `mod x; pub use x::*;` flattening all types into the crate root (helix-lsp-types/src/lib.rs:111-203), so consumers import `helix_lsp_types::CompletionItem` rather than the submodule path.

## Key facts

- TWO consumer-facing protocol traits define the request/notification contract: `pub trait Request { type Params; type Result; const METHOD: &'static str; }` (helix-lsp-types/src/request.rs:5-9) and `pub trait Notification { type Params; const METHOD: &'static str; }` (helix-lsp-types/src/notification.rs:5-8). Associated types are bounded `DeserializeOwned + Serialize + Send + Sync + 'static` (helix-lsp-types/src/request.rs:6-7).
- Two exported method-name→type lookup macros are the crate's public ergonomic API: `#[macro_export] macro_rules! lsp_request!` maps string method names like `"initialize"`/`"textDocument/completion"` to request structs (helix-lsp-types/src/request.rs:11-47), and `#[macro_export] macro_rules! lsp_notification!` does the same for notifications (helix-lsp-types/src/notification.rs:10-30).
- Scale of the modeled protocol: 65 `impl Request for` and 22 `impl Notification for` implementations across the crate (verified by source count over src/request.rs and src/notification.rs).
- A const-evaluated PascalCase formatter is a notable internal: `type PascalCaseBuf = [u8; 32]` with the comment "Large enough to contain any enumeration name defined in this crate", plus a `const fn fmt_pascal_case_const(...)` used inside the `lsp_enum!` macro for compile-time `TryFrom<&str>` parsing of LSP enum names (helix-lsp-types/src/lib.rs:28-105).
- Core geometric primitives are zero-based and end-exclusive by spec: `Position { line: u32, character: u32 }` (helix-lsp-types/src/lib.rs:244-253) and `Range { start, end }` where "the end position is exclusive" (helix-lsp-types/src/lib.rs:261-269).
- The `character` offset is encoding-relative, not byte/char-fixed: its meaning "is determined by the negotiated `PositionEncodingKind`" (helix-lsp-types/src/lib.rs:247-249) — a load-bearing invariant for any consumer converting LSP positions to buffer offsets.
- `bitflags` is used for exactly one wire type with a hand-written serde bridge: `WatchKind: u8 { Create=1, Change=2, Delete=4 }` (helix-lsp-types/src/lib.rs:2503-2513) serializes as a raw `u8` via custom `Serialize`/`Deserialize` impls that round-trip through `from_bits`/`bits` (helix-lsp-types/src/lib.rs:2515-2534).
- `#[allow(non_upper_case_globals)]` is set crate-wide to permit LSP-faithful constant casing (helix-lsp-types/src/lib.rs:17).
- Crate uses `edition = "2018"` and is versioned `0.95.1`, license MIT (helix-lsp-types/Cargo.toml:3, helix-lsp-types/Cargo.toml:11, helix-lsp-types/Cargo.toml:21).
<!-- DEEPINIT:END -->
