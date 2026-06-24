<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND)
 component: helix-dap-types
 path: helix-dap-types
 inputs: [helix-dap-types/Cargo.toml, helix-dap-types/src/lib.rs, Cargo.toml (workspace root, membership only)]
 doc_in_inputs: false
 method: re-derived from source + manifest only; no prose architecture docs consulted
-->

# Component: helix-dap-types

## Role

- A dependency-free, pure-data-model crate that defines the Rust serde-(de)serializable types, request/response shapes, and events for the Debug Adapter Protocol (DAP) — every item in the crate is a `#[derive(... Deserialize, Serialize)]` struct/enum or a marker-trait impl, with no behavior beyond serialization helpers (helix-dap-types/src/lib.rs:6-1093; helix-dap-types/Cargo.toml:3).

## Dependencies (edges)

- No outgoing edges to any other workspace component. The manifest `[dependencies]` lists only third-party `serde` and `serde_json`; there is no `helix-*` path/workspace dependency (helix-dap-types/Cargo.toml:13-15).
- No `use helix_*` / cross-crate reference exists anywhere in the source; the only imports are `serde`, `serde_json::Value`, `std::collections::HashMap`, `std::path::PathBuf` (helix-dap-types/src/lib.rs:1-4). A whole-directory search for "helix" matched only the crate's own package name, confirming a leaf crate (helix-dap-types/Cargo.toml:2).
- External (non-component) deps: `serde` with the `derive` feature, and `serde_json` (helix-dap-types/Cargo.toml:14-15).
- Consumer direction (incoming, for context, not an outgoing edge): `helix-dap` declares `helix-dap-types = { path = "../helix-dap-types" }` (helix-dap/Cargo.toml:18) and re-exports it wholesale via `pub use helix_dap_types::*;` (helix-dap/src/lib.rs:6).

## Data

- Owns NO runtime data store, file, or DB — it is a type-definition crate only; the sole I/O surface is serde (de)serialization of the declared types (helix-dap-types/src/lib.rs:6-9, 19-23).
- The wire data model it defines (all serde types): the `Request` trait keyed by `const COMMAND` (helix-dap-types/src/lib.rs:19-23); the `events::Event` trait keyed by `const EVENT` (helix-dap-types/src/lib.rs:798-801); request arg/response structs + zero-variant marker enums under `mod requests` (helix-dap-types/src/lib.rs:352-791); event body structs + marker enums under `mod events` (helix-dap-types/src/lib.rs:795-1086); shared payload structs `DebuggerCapabilities`, `Source`, `Breakpoint`, `StackFrame`, `Scope`, `Variable`, `Module`, etc. (helix-dap-types/src/lib.rs:25-333).

## Boundary rules

- Leaf/foundation layer of the workspace dependency DAG: it depends on no sibling crate, so it cannot participate in any intra-workspace import cycle (helix-dap-types/Cargo.toml:13-15). Cargo's cross-crate dependency-cycle ban makes such a cycle structurally impossible regardless.
- Separation of protocol *types* from protocol *behavior*: this crate holds only the DAP data model; the transport/client logic lives in the consuming `helix-dap` crate, which constrains its generic `call`/`request` methods over this crate's `Request` trait (helix-dap/src/client.rs:254, 301) and re-exports the types (helix-dap/src/lib.rs:6). The type crate never reaches back into a consumer.
- camelCase wire boundary: every protocol struct carries `#[serde(rename_all = "camelCase")]` so snake_case Rust fields map to the DAP JSON contract (e.g. helix-dap-types/src/lib.rs:26-27, 39, 54, 820); per-field overrides exist where DAP uses non-camelCase keys, e.g. `clientID`/`adapterID`/`linesStartAt1`/`columnsStartAt1` (helix-dap-types/src/lib.rs:357, 361, 365, 367) and `type` -> `ty` (helix-dap-types/src/lib.rs:32, 296, 698).
- Optional-field omission contract: optional fields use `#[serde(skip_serializing_if = "Option::is_none")]` so absent values are dropped from the wire payload rather than serialized as null (e.g. helix-dap-types/src/lib.rs:30, 43-50, 144-159).

## Key facts

- `ThreadId` is a newtype `pub struct ThreadId(isize)` deriving the full ordering/hashing set so it can key maps and be compared, with a manual `Display` forwarding to the inner `isize` (helix-dap-types/src/lib.rs:6-15); `ThreadStates` is the alias `HashMap<ThreadId, String>` (helix-dap-types/src/lib.rs:17).
- The dispatch model is type-level, not data-level: each request/event is a zero-variant marker enum (e.g. `pub enum Initialize {}`) whose protocol identity lives entirely in associated `const COMMAND`/`const EVENT` and associated `Arguments`/`Result`/`Body` types via the `Request`/`Event` traits — so command/event names are compile-time constants, not stringly-typed at the call site (helix-dap-types/src/lib.rs:19-23, 386-392, 798-817).
- Custom deserializer `from_number` coerces DAP's `Module.id` (which adapters send as either a JSON number or string) into a `String` via an `#[serde(untagged)]` `NumberOrString` helper enum (helix-dap-types/src/lib.rs:314-315, 335-350); both branches are covered by the only two tests in the crate (helix-dap-types/src/lib.rs:1095-1107).
- `ConnectionType` is a `#[serde(rename_all = "lowercase")]` enum `{ Launch, Attach }` used as the typed `request` discriminator of `StartDebuggingArguments` (helix-dap-types/src/lib.rs:1088-1093, 778-781).
- Several request payloads are deliberately untyped passthroughs to `serde_json::Value` — `Launch`/`Attach`/`Restart` arguments and `StartDebuggingArguments.configuration` — because their schema is adapter-defined (helix-dap-types/src/lib.rs:398, 406, 427, 781).
- Honest scope gaps left in code: the DAP `invalidated` event body is commented out (`InvalidatedBody`, helix-dap-types/src/lib.rs:1063-1069), `SetExceptionBreakpoints` omits `filterOptions`/`exceptionOptions` pending capability support (helix-dap-types/src/lib.rs:724-725), and `ProcessBody.start_method` is a `String` with a `// TODO: use enum` (helix-dap-types/src/lib.rs:1044).
- Version/authorship/license metadata is inherited from the workspace (`*.workspace = true`), so the crate carries no standalone version (helix-dap-types/Cargo.toml:4-11).
<!-- DEEPINIT:END -->
