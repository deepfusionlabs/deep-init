<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND re-derivation from code only)
 component: helix-event
 path: helix-event
 run: p5-mirror-blind
 inputs: helix-event/Cargo.toml, helix-event/src/{lib,registry,hook,runtime,debounce,cancel,redraw,status,test}.rs
 date: 2026-06-13
-->

# Component: helix-event

## Role

- A decoupling layer that lets editor components communicate without strong coupling, providing synchronous typed hooks dispatched on editor events plus async/debounced hooks and main-loop message queues (helix-event/src/lib.rs:1-5).

## Dependencies (edges)

- No outgoing edges to any other workspace member. The manifest's `[dependencies]` lists only external crates (foldhash, hashbrown, tokio, parking_lot, once_cell, anyhow, log, futures-executor) and no `helix-*` crate (helix-event/Cargo.toml:14-26).
- The crate source contains no `use helix_*` / path reference to another workspace component; the only `helix-` mentions are doc-comments describing how *other* crates consume this one (helix-view, helix-term are inbound consumers, not outgoing deps) (helix-event/src/lib.rs:26,30,32).
- Therefore helix-event is a foundational/leaf crate in the dependency DAG: depended-upon by others, depends on no other helix component (helix-event/Cargo.toml:14-26).

## Data

- Owns a process-global event Registry (events name->TypeId map + per-event handler vectors), stored in a `RwLock` behind a `runtime_local!` static REGISTRY (helix-event/src/registry.rs:16-19, 104-111).
- Owns global redraw-control state: a `Notify` (REDRAW_NOTIFY) and a `RwLock<>` render lock (RENDER_LOCK), both `runtime_local!` statics (helix-event/src/redraw.rs:10-21).
- Owns a global status-message queue: a `OnceCell<Sender<StatusMessage>>` MESSAGES static; `setup` creates the bounded(128) mpsc channel and returns the receiver to the caller (helix-event/src/status.rs:42-44, 64-68).
- Per-AsyncHook state lives in a bounded(128) tokio mpsc channel created per `spawn`, drained by a background task (helix-event/src/debounce.rs:25-37, 39-61).
- TaskController/TaskHandle cancellation state is a single `AtomicU64` packing a 32-bit generation (low) and 32-bit running-count (high), shared via `Arc<Shared>` plus a tokio `Notify` (helix-event/src/cancel.rs:24-40, 43-49, 56-71).

## Boundary rules

- Hooks run synchronously and receive only `&mut Event` (immutable closure state), so stateful/expensive/debounced work must move to an `AsyncHook` background tokio task instead (helix-event/src/lib.rs:13-23; helix-event/src/debounce.rs:9-37).
- Event types must be unique by `Event::ID` (their type name); registering two events with the same ID panics, and the registry enforces TypeId matching on register/dispatch to keep the erased dispatch sound (helix-event/src/registry.rs:25-40, 53-64, 85-93).
- `Event` is an `unsafe trait` whose impl details are private; events/hooks must be declared via the `events!` and `register_hook!` macros (not by hand) so the lifetime-count soundness invariant holds (helix-event/src/lib.rs:6-11, 110-133, 136-205; helix-event/src/registry.rs:121-131).
- Cross-channel sends from synchronous hooks must use the crate's `send_blocking` instead of tokio's `blocking_send`, to avoid the tokio-channel limitation (and `send_blocking` drops a message after a 10ms timeout rather than freezing the editor) (helix-event/src/lib.rs:18-22; helix-event/src/debounce.rs:63-70).
- `status::setup` must be called exactly once during editor startup before any status message is used; calling it twice panics (it is also the only way to obtain the message receiver) (helix-event/src/status.rs:59-68).

## Key facts

- The hook dispatch system is a hand-rolled inline vtable (`ErasedHook` stores `data: NonNull<Opaque>` + a single `call` fn pointer) rather than `dyn Trait`, to avoid double pointer indirection; it deliberately has no Drop because the registry is global and never dropped (helix-event/src/hook.rs:1-9, 25-28).
- `Opaque()` is an opaque erased-type-parameter handle used only behind references to preserve lifetimes since extern types are unstable (helix-event/src/hook.rs:16-23).
- A dispatched hook returning `Err` is logged via `log::error!` and routed to the status queue via `status::report_blocking` — a hook failure never aborts the remaining hooks for that event (helix-event/src/registry.rs:94-101).
- `register_hook_raw` is `unsafe`: the hook must be fully generic over all lifetime params of `E`; the `register_hook!` macro enforces this with a compile-time `ASSERT` comparing declared lifetime count against `Event::LIFETIMES` to reject unsound type aliases (helix-event/src/lib.rs:63-74, 184-203).
- The REGISTRY RwLock is essentially read-only after init (writes only register events/hooks at startup), and the manifest enables parking_lot's `hardware-lock-elision` feature so the read lock is nearly free when there are no writes (helix-event/Cargo.toml:18-21; helix-event/src/registry.rs:113-119).
- `runtime_local!` is a tokio-runtime-scoped static: a plain static normally, but under the `integration_test` feature it becomes a per-`tokio::runtime::Id` map (RwLock + leaked boxes) so multiple helix apps can run in parallel in one test process (helix-event/src/runtime.rs:1-12, 16-40, 42-89; helix-event/Cargo.toml:28-29).
- TaskController intentionally does not implement Clone and requires `&mut` for cancellation to avoid races in `inc_generation`; dropping a TaskController cancels its tasks, and `TaskHandle::is_canceled` is a single atomic read (cheap to poll from sync code) (helix-event/src/cancel.rs:116-117, 138-140, 157-161, 204-206).
- The registry hashers use foldhash with hardcoded fixed seeds (DOS-resistance explicitly waived as unnecessary) to avoid an `Option<Registry>` (helix-event/src/registry.rs:104-111).
- Redraws are debounced (comment says currently 30FPS) via `request_redraw`/`redraw_requested`; `lock_frame` returns a read guard that holds off the next frame until dropped, and `RequestRedrawOnDrop` is a ZST that requests a redraw on Drop (helix-event/src/redraw.rs:26-36, 49-62).
- `AsyncHook::spawn` only spawns the background worker when already inside a tokio runtime (`Handle::try_current.is_ok`), so unit tests don't need a runtime (helix-event/src/debounce.rs:31-36).
<!-- DEEPINIT:END -->
