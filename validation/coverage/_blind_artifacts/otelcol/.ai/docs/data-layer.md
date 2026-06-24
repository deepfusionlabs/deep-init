<!--
provenance:
 stage: blind-mirror-test
 repo: otelcol@blind
 doc_in_inputs: false
 generated_by: DeepInit EMIT/GENERATE (blind artifact)
 inputs: source files + build manifests (go.mod) + directory layout ONLY
 date: 2026-06-13
-->

# Data layer — otelcol (blind re-derivation)

**There is no application database.** Telemetry data is carried in-memory as `pdata`
OTLP proto structs (`consumer/traces.go:10`); persistence appears only in one place —
the exporter's optional file-storage-backed send queue. Below are all data-holding facts
grounded to `file:line`.

## pdata — the in-memory data model (no DB persistence)

- No external/DB persistence — storage is in-memory OTLP proto structs serialized by
 hand-written varint codecs (`pdata/internal/proto/marshal.go:7`,
 `pdata/internal/proto/unmarshal.go`, `pdata/internal/proto/size.go`).
- Optional `sync.Pool` memory pools for proto value structs, gated by the
 `pdata.useProtoPooling` alpha gate (pool defs at
 `pdata/internal/generated_proto_anyvalue.go:120`; gate-checked alloc at
 `pdata/internal/wrapper_value.go:31`).
- Serialized output forms: protobuf bytes via `ProtoMarshaler`/`ProtoUnmarshaler`
 (`pdata/plog/pb.go:8`, `pdata/plog/pb.go:35`) and JSON via in-house streaming codec
 `internal/json` (`pdata/plog/json.go:9`, `pdata/internal/json/stream.go`).

## exporter — the only persistence (send queue)

- **Persistent file-storage-backed send queue:** `persistentQueue[T]` is a durable FIFO
 backed by a `storage.Client`, with write/read indices + in-flight key + metadata key
 `qmv0` (legacy `ri`/`wi`/`di`)
 (`exporter/exporterhelper/internal/queue/persistent_queue.go:50-72,29-34`). Storage
 access is host-mediated — the queue obtains the storage extension via
 `host.GetExtensions`, else `errNoStorageClient`/`errWrongExtensionType`
 (`exporter/exporterhelper/internal/queue/persistent_queue.go:549-560,40-41`). The
 queue is keyed `component.KindExporter` when fetching its storage client
 (`exporter/exporterhelper/internal/queue/persistent_queue.go:560`).
- **In-memory send queue (default):** `QueueBatchConfig` stores 1000 requests,
 non-blocking when full, `ErrQueueIsFull` on overflow
 (`exporter/exporterhelper/queue_batch.go:38-42`).
- **External backend sink (not a local store):** OTLP gRPC `ClientConn` + clients
 (`exporter/otlpexporter/otlp.go:35-52,65-84`); otlphttp `*http.Client`
 (`exporter/otlphttpexporter/otlp.go:12,40`).

## receiver — in-process registry + telemetry counters (no store)

- In-process per-config singleton registry (no persistence): `receivers =
 sharedcomponent.NewMap[*Config, *otlpReceiver]` deduplicates one `otlpReceiver` per
 config across signal create calls (`receiver/otlpreceiver/factory.go:163`).
- Emits observability telemetry, not a store: per-signal accepted/refused/failed
 counters + the metric-key vocabulary `accepted_spans`/`refused_spans`/`failed_spans`/...
 (`receiver/receiverhelper/obsreport.go:256`,
 `receiver/receiverhelper/internal/obsmetrics.go:17`).

## processor — in-memory batch buffers (no persistence)

- In-memory pending-batch buffer per shard (batchprocessor), accumulated via
 `MoveAndAppendTo`, flushed by size/timeout — no persistence
 (`processor/batchprocessor/batch_processor.go:92`,
 `processor/batchprocessor/batch_processor.go:450`).
- Metadata-keyed shard map `multiShardBatcher.batchers` (`sync.Map` keyed by attribute
 set), guarded by mutex + size counter
 (`processor/batchprocessor/batch_processor.go:311`,
 `processor/batchprocessor/batch_processor.go:315-316`).

## connector — no persistence (in-memory routing only)

- No persistence: state is in-memory only — `BaseRouter` holds `Consumers
 map[pipeline.ID]T` (copied via `maps.Copy`) and a fanout func
 (`connector/internal/router.go:16-25`).

## service — in-memory pipeline DAG + config object (no persistent store)

- In-memory pipeline DAG only — `componentGraph *simple.DirectedGraph` (gonum) plus
 `pipelines map[pipeline.ID]*pipelineNodes` and
 `instanceIDs map[int64]*componentstatus.InstanceID`
 (`service/internal/graph/graph.go:62,65,68`).
- Reads the collector config object in memory (`CollectorConf *confmap.Conf`); does not
 load config from disk itself (`service/service.go:48`, `service/service.go:125`).
- No persistent store; emits internal process/runtime metrics and per-component
 item/size counters as telemetry output (`service/metadata.yaml:74`,
 `service/metadata.yaml:171`).

## otelcol — in-memory log buffer + read-only config (no persistent store)

- In-memory zap log buffer (`bufferedCore`) that captures early logs then drains once
 via `TakeLogs` (`otelcol/buffered_core.go:26`, `otelcol/buffered_core.go:71`).
- Read-only config source resolved/watched/re-read via `confmap.Resolver` behind
 `ConfigProvider`; never written back (`otelcol/configprovider.go:24`,
 `otelcol/configprovider.go:55`, `otelcol/configprovider.go:83`).

## consumer / component — no production persistence

- consumer has no production persistence; the only data-holding type is the in-memory
 test sink `consumertest.TracesSink`/`MetricsSink`/`LogsSink`/`ProfilesSink` which
 buffers received payloads in mutex-guarded slices for test assertions only
 (`consumer/consumertest/sink.go:20`, `consumer/consumertest/sink.go:32`).
- component declares no data stores (`component/component.go:25` — contract layer only).
