<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND, code-only re-derivation)
 component: processor
 path: processor/
 inputs: processor/**/*.go (non-test), processor/go.mod, processor/*/go.mod, processor/metadata.yaml
 date: 2026-06-13
 rule: R1 (every claim grounded to file:line; prose docs excluded)
-->

# Component: processor

The `processor` component is a Go multi-module group rooted at `processor/`: the core
contract module `go.opentelemetry.io/collector/processor` (processor/go.mod:1) plus the
sub-modules `processorhelper` (processor/processorhelper/go.mod:1), `xprocessor`
(processor/xprocessor/go.mod:1), `batchprocessor`, and `memorylimiterprocessor`
(processor/memorylimiterprocessor/go.mod:1).

## Role

- Defines the pipeline-middle component contract: a processor consumes one telemetry
 signal, optionally transforms it, and forwards it to the next consumer in the pipeline —
 its three signal interfaces each embed `component.Component` + the matching
 `consumer.*` (processor/processor.go:16-31).

## Dependencies (edges)

- consumer — the processor signal interfaces ARE consumers: `Traces` embeds
 `consumer.Traces`, `Metrics` embeds `consumer.Metrics`, `Logs` embeds `consumer.Logs`
 (processor/processor.go:10, processor/processor.go:16-31).
- consumer — `Factory.Create*` take the downstream `next consumer.*` as the forwarding
 target ("Implementers can assume `next` is never nil") (processor/processor.go:58, processor/processor.go:67, processor/processor.go:76).
- component — every processor interface embeds `component.Component`; the `Factory` embeds
 `component.Factory`; `Settings` carries `component.ID`, `component.TelemetrySettings`,
 `component.BuildInfo` (processor/processor.go:9, processor/processor.go:17, processor/processor.go:52, processor/processor.go:34-45).
- pipeline — unsupported-signal `Create*` calls return the shared sentinel
 `pipeline.ErrSignalNotSupported` (processor/processor.go:12, processor/processor.go:131, processor/processor.go:143, processor/processor.go:155).
- consumer/xconsumer — the experimental `xprocessor.Profiles` interface embeds
 `xconsumer.Profiles` and `CreateProfiles` takes `next xconsumer.Profiles`
 (processor/xprocessor/processor.go:10, processor/xprocessor/processor.go:33-36, processor/xprocessor/processor.go:66).
- pdata — `processorhelper.NewTraces` wraps a `ProcessTracesFunc(ctx, ptrace.Traces)` and
 counts items via `td.SpanCount` (processor/processorhelper/traces.go:15, processor/processorhelper/traces.go:22, processor/processorhelper/traces.go:56); the batcher batches `ptrace.Traces`/`pmetric.Metrics`/`plog.Logs` (processor/batchprocessor/batch_processor.go:23-25).
- consumer/consumererror — batch processor returns a permanent error when the metadata
 cardinality limit is hit (processor/batchprocessor/batch_processor.go:22, processor/batchprocessor/batch_processor.go:31).
- client — batch processor carries per-shard metadata in a `client.Info`/`client.Metadata`
 context for metadata-keyed sharding (processor/batchprocessor/batch_processor.go:19, processor/batchprocessor/batch_processor.go:154-156, processor/batchprocessor/batch_processor.go:326).
- internal/memorylimiter — `memorylimiterprocessor` delegates all admission control to the
 shared `memorylimiter.MemoryLimiter` (`MustRefuse`, `ErrDataRefused`) (processor/memorylimiterprocessor/memorylimiter.go:10, processor/memorylimiterprocessor/memorylimiter.go:21, processor/memorylimiterprocessor/memorylimiter.go:27, processor/memorylimiterprocessor/memorylimiter.go:54).

## Data

- No external/persistent data store. The batch processor owns an IN-MEMORY pending-batch
 buffer per shard (`shard.batch`, accumulated via `MoveAndAppendTo`) flushed by size or
 timeout (processor/batchprocessor/batch_processor.go:92, processor/batchprocessor/batch_processor.go:450, processor/batchprocessor/batch_processor.go:38-40).
- Metadata-keyed sharding state: `multiShardBatcher.batchers sync.Map` keyed by the
 attribute set, guarded by a mutex + size counter (processor/batchprocessor/batch_processor.go:311, processor/batchprocessor/batch_processor.go:315-316, processor/batchprocessor/batch_processor.go:341).

## Boundary rules

- Multi-module boundary: the contract module declares only first-party deps via local
 `replace` directives (component/consumer/pdata/pipeline/componentalias), and each
 sub-module replaces the parent `processor =>../` — a build-manifest DAG, no version drift
 (processor/go.mod:35-55, processor/processorhelper/go.mod:6).
- A processor MUST NOT call the next component on error: "If error is returned then
 returned data are ignored. It MUST not call the next component"
 (processor/processorhelper/traces.go:21, processor/processorhelper/xprocessorhelper/profiles.go:19).
- `ErrSkipProcessingData` is a sentinel to drop data WITHOUT propagating an error up the
 pipeline (processor/processorhelper/processor.go:22, processor/processorhelper/traces.go:64).
- `Factory` is sealed: it cannot be implemented directly — `unexportedFactoryFunc` forces
 construction through `NewFactory` (processor/processor.go:49-51, processor/processor.go:81, processor/processor.go:199).
- Component-type/ID validation gate: every `Create*` runs
 `componentalias.ValidateComponentType(f, set.ID)` before constructing
 (processor/processor.go:134, processor/processor.go:146, processor/processor.go:158, processor/xprocessor/processor.go:70).

## Key facts

- Default processor capability is `MutatesData: true` — processors are assumed to mutate
 data unless `WithCapabilities` overrides it (processor/processorhelper/processor.go:69, processor/batchprocessor/batch_processor.go:166-167).
- The signal set is Traces/Metrics/Logs in the stable contract; Profiles is split into the
 experimental `xprocessor`/`xprocessorhelper` packages, not the core interface
 (processor/processor.go:16-31, processor/xprocessor/processor.go:32-36).
- `processorhelper` wraps a per-signal `Process*Func` into a `consumer.New*`, auto-recording
 in/out item counts + internal duration as OTel telemetry around each call
 (processor/processorhelper/traces.go:50-72, processor/processorhelper/obsreport.go:40-48).
- Observability identifies processors with the constant attribute key `"processor"`
 (`internal.ProcessorKey`) and a metric prefix `processor_`
 (processor/internal/obsmetrics.go:10, processor/internal/obsmetrics.go:12).
- Batch processor flushes on `SendBatchSize` reached OR `Timeout` elapsed (defaults 8192 /
 200ms), with per-shard goroutine + timer loops (processor/batchprocessor/batch_processor.go:38-40, processor/batchprocessor/factory.go:19-20, processor/batchprocessor/batch_processor.go:189-225).
- Memory-limiter processor is a pure admission gate: on `MustRefuse` it returns the data
 unchanged plus `ErrDataRefused`; it never transforms payload
 (processor/memorylimiterprocessor/memorylimiter.go:54-64).
<!-- DEEPINIT:END -->
