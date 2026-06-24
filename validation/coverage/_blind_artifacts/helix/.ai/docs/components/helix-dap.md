<!--
DEEPINIT EXTRACT — component doc
stage: extract
component: helix-dap
run: blind-rederive
inputs: helix-dap/Cargo.toml, helix-dap/src/{lib.rs,client.rs,transport.rs,registry.rs}
date: 2026-06-13
provenance: BLIND re-derivation from source + manifest only (no prose/arch docs read)
-->

# Component: helix-dap

## Role

- A Debug Adapter Protocol (DAP) client library: spawns a debug-adapter process, speaks DAP over stdio or TCP, and exposes typed request/event/registry APIs to drive a debugging session (helix-dap/Cargo.toml:3; helix-dap/src/client.rs:30; helix-dap/src/registry.rs:12).

## Dependencies (edges)

- helix-dap-types — path dependency; the entire crate's typed DAP surface is re-exported (`pub use helix_dap_types::*`) and request/event command types come from it (helix-dap/Cargo.toml:18; helix-dap/src/lib.rs:6; helix-dap/src/client.rs:8).
- helix-dap-types — bound on every RPC call via the `helix_dap_types::Request` trait (`R::COMMAND`, `R::Arguments`, `R::Result`) (helix-dap/src/client.rs:254; helix-dap/src/client.rs:301; helix-dap/src/lib.rs:46-47).
- helix-core — path dependency; consumes `helix_core::syntax::config::{DebugAdapterConfig, DebuggerQuirks}` to configure/start a client (helix-dap/Cargo.toml:17; helix-dap/src/client.rs:7; helix-dap/src/registry.rs:4).
- helix-stdx — path dependency; uses `helix_stdx::env::which` to resolve the adapter binary path and converts its `ExecutableNotFoundError` into the crate error (helix-dap/Cargo.toml:16; helix-dap/src/client.rs:120; helix-dap/src/lib.rs:26).
- (No outgoing edges to helix-view, helix-term, helix-tui, helix-lsp, helix-lsp-types, helix-event, helix-loader, helix-vcs, helix-parsec, or xtask — none appear in the manifest [helix-dap/Cargo.toml:15-30] or in any source import [verified across src/lib.rs, client.rs, transport.rs, registry.rs].)

## Data

- Owns no persistent/disk store. All state is in-memory per `Client`: a `Child` process handle, `socket: Option<SocketAddr>`, capabilities, `stack_frames: HashMap<ThreadId, Vec<StackFrame>>`, `thread_states`, `progress`, and the starting-request args (helix-dap/src/client.rs:30-50).
- `Transport` holds the correlation table `pending_requests: Mutex<HashMap<u64, Sender<Result<Response>>>>` mapping request `seq` → reply channel (helix-dap/src/transport.rs:56).
- `Registry` owns all live clients in a `SlotMap<DebugAdapterId, Client>` plus a `SelectAll` stream multiplexing every adapter's incoming messages (helix-dap/src/registry.rs:13-20).
- Reads the spawned adapter's stdout/stdin/stderr (or a TCP socket) as its only external I/O; the config (command/args/transport) is read from `DebugAdapterConfig`, not from a store this crate owns (helix-dap/src/client.rs:122-145; helix-dap/src/registry.rs:38-54).

## Boundary rules

- Wire framing follows the DAP/LSP base protocol: each message is a `Content-Length: N\r\n\r\n` header block followed by the JSON body; reader loops until an empty `\r\n` then reads exactly N bytes (helix-dap/src/transport.rs:94-123; helix-dap/src/transport.rs:173-178).
- Message sequencing invariant: the first `seq` is 1 and each subsequent is +1, via an `AtomicU64` counter incremented before use (helix-dap/src/client.rs:235-241).
- Responses are demultiplexed by `request_seq` against `pending_requests`; a response with no matching pending request is forwarded to the client channel with a warning rather than dropped (helix-dap/src/transport.rs:209-225).
- Layer separation: the `Transport` task pair (recv/send) is the only code touching the raw streams; the `Client` communicates with it solely through `UnboundedSender<Payload>` / callback channels — no shared mutable state across the boundary (helix-dap/src/client.rs:79-100; helix-dap/src/transport.rs:60-83).
- `recv` asserts the server never sends a bare `Response` up the server→client path (`Payload::Response(_) => unreachable!`), since responses are consumed by the transport's correlation layer (helix-dap/src/client.rs:217).

## Key facts

- Two transports are supported and selected by a `(transport, port_arg)` match: `"tcp"` (spawn + connect to 127.0.0.1:port) or `"stdio"` (spawn + pipe); anything else is an error (helix-dap/src/client.rs:65-69).
- TCP startup uses a fixed 500ms sleep to wait for the adapter to become ready before connecting — a timing assumption, not a readiness handshake (helix-dap/src/client.rs:184).
- Transport choice changes process-reaping policy: stdio spawns with `kill_on_drop(true)` (adapter dies with Helix), while tcp_process deliberately does NOT, so the adapter exits on its own (helix-dap/src/client.rs:128; helix-dap/src/client.rs:180-181).
- RPC requests have a hard-coded 20-second timeout; on expiry an `Error::Timeout(seq)` is returned (helix-dap/src/client.rs:284-286). The TODO notes the timeout is not yet configurable.
- Dual JSON stack: incoming server messages are parsed with `sonic-rs` (`sonic_rs::from_slice`) for speed while outgoing payloads are serialized with `serde_json` — both error types are funneled into `Error::Parse` (helix-dap/src/transport.rs:131; helix-dap/src/transport.rs:161; helix-dap/src/lib.rs:32-42).
- Non-conformant adapters are tolerated: header lines that aren't `key: value` are silently skipped (debug adapters/shell wrappers that leak logging into the stream don't crash the parser) (helix-dap/src/transport.rs:111-118).
- `DebugAdapterId` is a slotmap key type (`new_key_type!`), giving each client a generational id reused as the message-tagging key so multiplexed streams can be attributed to a client (helix-dap/src/registry.rs:106-108; helix-dap/src/registry.rs:51).
- `Registry::start_client` bridges async into a sync API by wrapping each step in `futures_executor::block_on` (tcp/process spawn, then `initialize`) (helix-dap/src/registry.rs:39-54).
- `initialize` hard-codes Helix's client identity and declared capabilities (`client_id="hx"`, `client_name="helix"`, supports run-in-terminal, progress reporting; declines memory-references and invalidated-event) (helix-dap/src/client.rs:371-389).
- `configuration_done` is gated on the adapter's advertised `supports_configuration_done_request` capability — sent only if supported, otherwise a no-op (helix-dap/src/client.rs:456-468).
- `restart` replays the originally-stored launch/attach arguments (`starting_request_args`), defaulting to `Value::Null` if none were stored (helix-dap/src/client.rs:422-428).
- The crate exposes higher-level wrappers over Helix-specific concepts: `Registry` models a single "active client" but flags in a TODO that multiple concurrent active debuggers aren't yet modeled (helix-dap/src/registry.rs:15-18).
- `ProgressState` aggregates DAP progress events into human-readable status lines (`"Debug: <title> - <msg> (<pct>%)"`), keyed by `progress_id` in a `ProgressMap = HashMap<String, ProgressState>` (helix-dap/src/lib.rs:122-171; helix-dap/src/client.rs:353-369).
