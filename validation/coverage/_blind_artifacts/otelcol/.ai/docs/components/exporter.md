<!-- Provenance: stage=EXTRACT component=exporter run=p5-blind inputs=exporter/ (source + go.mod manifests) date=2026-06-13 -->
# Component: exporter

Blind re-derivation from code only (exporter/ source + go.mod manifests + directory layout). Every bullet ends with its file:line.

## Role

- The egress tier of the collector pipeline: defines the `Traces`/`Metrics`/`Logs` exporter interfaces (each = a `component.Component` that is also a `consumer` of the matching signal) and the `Factory` that creates them from config — i.e. the terminal component that consumes pipeline telemetry and sends it to an external destination — exporter/exporter.go:16-31, exporter/exporter.go:51-79.
- `metadata.yaml` self-declares `type: exporter` (a `pkg`-class library, not a leaf component) — exporter/metadata.yaml:1-6.

## Dependencies (edges)

- **component** — every exporter interface embeds `component.Component`; `Factory` embeds `component.Factory`; `Settings` carries `component.ID`/`TelemetrySettings`/`BuildInfo`; module require + local `replace../component` — exporter/exporter.go:9, exporter/exporter.go:17, exporter/exporter.go:34-44, exporter/go.mod:7, exporter/go.mod:60.
- **consumer** — the exporter interfaces ARE consumers (`consumer.Traces`/`Metrics`/`Logs`); exporterhelper builds exporters from `consumer.ConsumeTracesFunc` pushers; module require + `replace../consumer` — exporter/exporter.go:10, exporter/exporter.go:18,24,30, exporter/exporterhelper/traces.go:21, exporter/go.mod:10, exporter/go.mod:64.
- **pipeline** — unsupported signals return `pipeline.ErrSignalNotSupported`; persistent queue keys client by `pipeline.Signal`; module require + `replace../pipeline` — exporter/exporter.go:12,137, exporter/exporterhelper/internal/queue/persistent_queue.go:21,560, exporter/go.mod:15, exporter/go.mod:74.
- **pdata** — the OTLP exporter marshals `ptrace/pmetric/plog/pprofile` into OTLP export requests; module require + `replace../pdata` — exporter/otlpexporter/otlp.go:25-32,98, exporter/go.mod:14, exporter/go.mod:68.
- **extension (storage)** — the persistent queue resolves a storage *extension* from the host and gets a `storage.Client` keyed `KindExporter` — a runtime extension→exporter coupling; `replace../extension` (+ `xextension`) — exporter/exporterhelper/internal/queue/persistent_queue.go:20,549-561, exporter/go.mod:42-43, exporter/go.mod:66.
- **receiver** — declared as a sibling-module `replace` target in both manifests (build-graph edge; used by exporterhelper test rigs) — exporter/go.mod:76, exporter/exporterhelper/go.mod:66-67,93.
- **config/configgrpc, config/configretry, config/configoptional** — OTLP egress dials a gRPC ClientConn via configgrpc; retry/backoff is `configretry.BackOffConfig`; queue config is `configoptional.Optional` — exporter/otlpexporter/otlp.go:20,67, exporter/exporterhelper/common.go:10,38, exporter/exporterhelper/queue_batch.go:9,18.
- **internal/componentalias** — the factory holds a `TypeAliasHolder` and calls `ValidateComponentType` before every Create; `replace../internal/componentalias` — exporter/exporter.go:11,108,140, exporter/go.mod:13, exporter/go.mod:116.

## Data

- **Persistent (file-storage-backed) send queue** — `persistentQueue[T]` is a durable FIFO backed by a `storage.Client` from a storage extension; write/read indices, in-flight items kept under a separate key until processing finishes, metadata under single key `qmv0` (legacy keys `ri`/`wi`/`di`) — exporter/exporterhelper/internal/queue/persistent_queue.go:50-72, exporter/exporterhelper/internal/queue/persistent_queue.go:29-34, exporter/exporterhelper/internal/queue/persistent_queue.go:72-90.
- **In-memory send queue (default)** — default `QueueBatchConfig` stores 1000 requests, non-blocking when full; `ErrQueueIsFull` surfaces overflow — exporter/exporterhelper/queue_batch.go:38-42.
- **External backend (the egress sink)** — OTLP exporter holds gRPC clients + a `grpc.ClientConn` to a remote endpoint (exporter/otlpexporter/otlp.go:35-52,65-84); otlphttp exporter holds an `*http.Client` (exporter/otlphttpexporter/otlp.go:12,40).

## Boundary rules

- **Factory is sealed**: `Factory` cannot be implemented directly — `unexportedFactoryFunc` + "must use NewFactory" forces construction through the package — exporter/exporter.go:47-50,78,196-206.
- **Component-type validation gate**: every CreateTraces/Metrics/Logs validates the requested type against the factory before delegating — exporter/exporter.go:140-142,152-154,164-166.
- **Signal-capability gate**: a nil create-func returns `pipeline.ErrSignalNotSupported` rather than a panic — an exporter advertises only the signals it supports — exporter/exporter.go:135-138,147-149,159-162.
- **Experimental surface is segregated** in the `xexporter` submodule (the `Profiles` signal) which wraps a core `exporter.Factory` — keeping unstable signals out of the stable `exporter` API — exporter/xexporter/exporter.go:16-32,87-118.
- **Storage access is host-mediated**: the queue never opens files itself; it must obtain a storage extension via `host.GetExtensions`, erroring `errNoStorageClient`/`errWrongExtensionType` otherwise — exporter/exporterhelper/internal/queue/persistent_queue.go:549-560, exporter/exporterhelper/internal/queue/persistent_queue.go:40-41.

## Key facts

- **Multi-module component**: exporter/ ships 8 go.mod modules (root + exporterhelper, exportertest, xexporter, debugexporter, otlpexporter, otlphttpexporter, nopexporter); modules are wired with local `replace` directives into a build-MANIFEST DAG (sibling deps reference `../component`, `./exporterhelper`, etc.) — exporter/go.mod:1, exporter/go.mod:60-118, exporter/exporterhelper/go.mod:1,75-132.
- **exporterhelper is the reusable resilience toolkit** layered on top of the bare interfaces: configurable timeout (default 5s), retry/backoff (disabled by default), queue+batch, capabilities, start/shutdown — assembled via functional `Option`s — exporter/exporterhelper/common.go:18-53.
- **Retry classification by gRPC status**: OTLP egress retries on Canceled/DeadlineExceeded/Aborted/OutOfRange/Unavailable/DataLoss (ResourceExhausted only if server sent RetryInfo), wraps server-throttle delays via `NewThrottleRetry`, and marks non-retryable errors `consumererror.NewPermanent` — exporter/otlpexporter/otlp.go:173-222, exporter/exporterhelper/retry_sender.go:12-15.
- **Partial-success handling**: OTLP push paths log a warning with rejected-span/datapoint/log/profile counts instead of failing the whole request — exporter/otlpexporter/otlp.go:103-109,123-129,143-149,163-169.
- **gRPC client construction is deferred to Start** (not newExporter) because only there is the host available to build the auth round-tripper from Extensions — exporter/otlpexporter/otlp.go:63-67.
- **Bundled reference exporters** ship in-tree: otlp (gRPC), otlphttp (HTTP), debug (otlptext console dump), nop (no-op via xexporter, supports profiles) — exporter/otlpexporter/otlp.go:4, exporter/otlphttpexporter/otlp.go:4,40, exporter/debugexporter/factory.go:4,18, exporter/nopexporter/nop_exporter.go:16-25.
- **Tiny shared error helper** `experr.ErrIDMismatch` for component type/ID mismatches — exporter/internal/experr/err.go:12-14.
