<!-- DEEPINIT:START -->
<!--
provenance:
 stage: blind-mirror-test
 repo: otelcol@blind
 doc_in_inputs: false
 generated_by: DeepInit EMIT/GENERATE (blind artifact)
 inputs: source files + build manifests (go.mod) + directory layout ONLY
 date: 2026-06-13
 rule: every claim cites a file:line opened inside C:/tmp/p5_otelcol_blind
-->

# otelcol — Agent Context (AGENTS.md)

## Architecture

otelcol is a Go multi-module project (`go.mod:11`) implementing an OpenTelemetry-style
telemetry collector. The system is a strictly layered DAG built from sealed-factory
component contracts. At the foundation sits `component`, which defines the `Component`
lifecycle interface (Start/Shutdown) that every receiver, exporter, processor,
connector and extension must implement (`component/component.go:25`). On top of it,
`pdata` is the canonical in-memory data model for all pipeline signals
(traces/metrics/logs/profiles + shared pcommon) (`pdata/doc.go:6`), and `consumer`
defines the per-signal interfaces that receive pipeline data and forward it on
(`consumer/logs.go:15`). The four pipeline component kinds layer above those contracts:
`receiver` (pipeline ingress — translates external data to pdata and pushes it to the
next consumer, `receiver/receiver.go:20`), `processor` (pipeline-middle — consumes,
optionally transforms, and forwards a signal, `processor/processor.go:16-31`),
`exporter` (egress — the terminal component that sends telemetry to an external
destination, `exporter/exporter.go:16-31`), and `connector` (bridges one pipeline's
egress into one-or-more downstream pipelines, `connector/connector.go:16-18`).
`service` is the runtime orchestrator that builds the in-memory pipeline DAG, wires the
components, and owns their lifecycle as the concrete `component.Host`
(`service/service.go:99`). `otelcol` is the CLI + lifecycle layer whose `Collector.Run`
starts the collector and blocks until shutdown (`otelcol/collector.go:329`). Each
component is its own Go module wired to siblings via local `replace` directives, so the
build manifest is the dependency-DAG source of truth (`receiver/go.mod:1`,
`service/go.mod:1`).

## Component registry

| component | role | path / anchor |
|-----------|------|---------------|
| receiver | Pipeline ingress: defines the Traces/Metrics/Logs/Profiles interfaces + Factory; translates external-format data into internal pdata and pushes it to the next consumer | `receiver/` — `receiver/receiver.go:20` (anchor `versions.yaml:32`) |
| processor | Pipeline-middle: consumes one signal, optionally transforms it, forwards to the next consumer | `processor/` — `processor/processor.go:16-31` (anchor `versions.yaml:31`) |
| exporter | Egress tier: terminal pipeline component that consumes telemetry and sends it to an external destination | `exporter/` — `exporter/exporter.go:16-31` (anchor `versions.yaml:27`) |
| connector | Joins pipelines: acts as an exporter from one pipeline and a receiver to one-or-more downstream pipelines | `connector/` — `connector/connector.go:16-18` (anchor `versions.yaml:53`) |
| service | Runtime orchestrator + graph builder: assembles the pipeline DAG, owns component lifecycle, is the concrete `component.Host` | `service/` — `service/service.go:99` (anchor `service/service.go:43`) |
| otelcol | Collector entry: CLI + lifecycle; `Collector.Run` starts and blocks until shutdown | `otelcol/` — `otelcol/collector.go:329` (anchor `otelcol/collector.go:7`) |
| pdata | Data model: canonical in-memory data model for all pipeline signals + proto/JSON (un)marshalers | `pdata/` — `pdata/doc.go:6` (anchor `versions.yaml:10`) |
| consumer | Signal interfaces: per-signal Traces/Metrics/Logs (+experimental Profiles) consumer contracts + `BaseConsumer.Capabilities` | `consumer/` — `consumer/logs.go:15` (anchor `consumer/consumer.go:4`) |
| component | Component interface: the foundational lifecycle interface + shared ID/Type/Kind/Config/Host contracts | `component/` — `component/component.go:25` (anchor `component/component.go:25`) |

## Technical dependencies

- receiver -> component (import / interface-embed) — `receiver/receiver.go:21`
- receiver -> consumer (import / runtime-call, next sink) — `receiver/receiver.go:67`
- receiver -> pipeline (import / sentinel-error + Signal switch) — `receiver/receiver.go:147`
- receiver -> pdata (import, otlp wire types via otlpreceiver) — `receiver/otlpreceiver/otlp.go:22`
- receiver -> consumer (import xconsumer.Profiles, experimental signal) — `receiver/xreceiver/receiver.go:35`
- receiver -> component (project-ref, go.mod replace../component) — `receiver/go.mod:35`
- receiver -> consumer (project-ref, go.mod replace../consumer) — `receiver/go.mod:37`
- receiver -> pdata (project-ref, go.mod replace../pdata) — `receiver/go.mod:39`
- receiver -> pipeline (project-ref, go.mod replace../pipeline) — `receiver/go.mod:51`
- processor -> consumer (import / interface-embed) — `processor/processor.go:10`, `processor/processor.go:16-31`
- processor -> consumer (runtime-call, next consumer forwarding in Factory.Create*) — `processor/processor.go:58`, `processor/processor.go:67`, `processor/processor.go:76`
- processor -> component (import / interface-embed) — `processor/processor.go:9`, `processor/processor.go:17`, `processor/processor.go:52`
- processor -> pipeline (import, ErrSignalNotSupported sentinel) — `processor/processor.go:12`, `processor/processor.go:131`
- processor -> consumer (import consumer/xconsumer.Profiles in xprocessor) — `processor/xprocessor/processor.go:10`, `processor/xprocessor/processor.go:33-36`
- processor -> pdata (import ptrace/pmetric/plog in processorhelper + batchprocessor) — `processor/processorhelper/traces.go:15`, `processor/batchprocessor/batch_processor.go:23-25`
- processor -> consumer (import consumer/consumererror permanent error in batchprocessor) — `processor/batchprocessor/batch_processor.go:22`
- processor -> component (import client.Info/Metadata context for batch sharding) — `processor/batchprocessor/batch_processor.go:19`, `processor/batchprocessor/batch_processor.go:154-156`
- exporter -> component (import / interface-embed / project-ref) — `exporter/exporter.go:9,17`, `exporter/go.mod:7,60`
- exporter -> consumer (import / interface-embed — exporter IS a consumer / project-ref) — `exporter/exporter.go:10,18`, `exporter/exporterhelper/traces.go:21`, `exporter/go.mod:10,64`
- exporter -> pipeline (import / runtime-call ErrSignalNotSupported, Signal key / project-ref) — `exporter/exporter.go:12,137`, `exporter/exporterhelper/internal/queue/persistent_queue.go:560`, `exporter/go.mod:15,74`
- exporter -> pdata (import / runtime-call marshal ptrace/pmetric/plog/pprofile to OTLP / project-ref) — `exporter/otlpexporter/otlp.go:25-32,98`, `exporter/go.mod:14,68`
- exporter -> extension (runtime-call host.GetExtensions -> storage.Extension -> storage.Client / project-ref) — `exporter/exporterhelper/internal/queue/persistent_queue.go:20,549-561`, `exporter/go.mod:42,66`
- exporter -> receiver (project-ref, local replace, build-graph edge) — `exporter/go.mod:76`, `exporter/exporterhelper/go.mod:66-67,93`
- exporter -> component (runtime-call componentalias.ValidateComponentType before each Create) — `exporter/exporter.go:11,108,140`, `exporter/go.mod:116`
- connector -> consumer (import / interface-embed; routers typed over consumer types) — `connector/connector.go:11,28-31`, `connector/logs_router.go:13`
- connector -> consumer (project-ref, go.mod require + replace../consumer) — `connector/go.mod:8,39`
- connector -> component (import / interface-embed component.Component/Factory/ID/TelemetrySettings/BuildInfo) — `connector/connector.go:9,29,82,65-75`
- connector -> component (project-ref, go.mod require + replace../component) — `connector/go.mod:7,37`
- connector -> pdata (project-ref, go.mod require + replace../pdata; data model carried via consumers) — `connector/go.mod:12,41`
- connector -> pipeline (import / runtime-call; routers key by pipeline.ID; errors cite pipeline.Signal*) — `connector/logs_router.go:15,21`, `connector/connector.go:310`, `connector/internal/factory.go:14`
- connector -> pipeline (project-ref, go.mod require + replace../pipeline) — `connector/go.mod:14,51`
- connector -> internal/fanoutconsumer (import / runtime-call fanoutconsumer.NewLogs/NewMetrics/NewTraces) — `connector/logs_router.go:14,37`, `connector/go.mod:11,55`
- connector -> internal/componentalias (import / runtime-call TypeAliasHolder + ValidateComponentType in every Create*) — `connector/connector.go:12,238,313`, `connector/go.mod:10,53`
- connector -> consumer/xconsumer (import; xconnector profiles surface typed over xconsumer.Profiles) — `connector/xconnector/connector.go:13,55`, `connector/go.mod:27,47`
- connector -> pipeline/xpipeline (import; xconnector error paths cite xpipeline.SignalProfiles) — `connector/xconnector/connector.go:16,274`
- service -> receiver (import) — `service/service.go:26`
- service -> processor (import) — `service/service.go:25`
- service -> exporter (import) — `service/service.go:22`
- service -> connector (import) — `service/service.go:21`
- service -> extension (import) — `service/service.go:23`
- service -> component (import + runtime-call node.(component.Component).Start/Shutdown) — `service/internal/graph/graph.go:417`
- service -> consumer (import + runtime-wiring consumer.Traces/Metrics/Logs + Capabilities) — `service/internal/graph/graph.go:312`
- service -> pdata (import pcommon.NewResource) — `service/service.go:24`
- service -> otelcol (project-ref, go.mod require + local replace../otelcol; no source import in this component) — `service/go.mod:241`
- otelcol -> service (runtime-call) — `otelcol/collector.go:212`
- otelcol -> service (import) — `otelcol/collector.go:25`
- otelcol -> component (import) — `otelcol/factories.go:9`
- otelcol -> receiver (import) — `otelcol/factories.go:15`
- otelcol -> processor (import) — `otelcol/factories.go:14`
- otelcol -> exporter (import) — `otelcol/factories.go:11`
- otelcol -> extension (import) — `otelcol/factories.go:12`
- otelcol -> connector (import) — `otelcol/factories.go:10`
- otelcol -> consumer (project-ref) — `otelcol/go.mod:20`
- otelcol -> pdata (project-ref) — `otelcol/go.mod:94`
- pdata -> featuregate (import; registers pdata.useProtoPooling) — `pdata/internal/metadata/generated_feature_gates.go:6` (registers at `:9`); manifest replace `pdata/go.mod:36`
- pdata -> client (import, xpdata sub-module only, not root) — `pdata/xpdata/request/context.go:11`; required at `pdata/xpdata/go.mod:8` with replace =>../../client
- consumer -> pdata (import signal payload types plog.Logs/ptrace.Traces/pmetric.Metrics) — `consumer/logs.go:10`
- consumer -> pdata (project-ref, go.mod require + local replace../pdata) — `consumer/go.mod:7`
- consumer -> pdata (import pprofile.Profiles for experimental xconsumer.Profiles) — `consumer/xconsumer/profiles.go:12`
- consumer -> consumer (import; xconsumer subpackage imports parent consumer.Option + internal) — `consumer/xconsumer/profiles.go:10`
- consumer -> pdata (import consumererror signal-error wrappers on plog/pmetric/ptrace/pprofile) — `consumer/consumererror/internal/retryable.go:7`
- component -> pdata (import pcommon type-ref: TelemetrySettings.Resource pcommon.Resource) — `component/telemetry.go:11`
- component -> pdata (project-ref, direct require + replace =>../pdata) — `component/go.mod:6`
- component -> pdata (import componentstatus: Event.attributes pcommon.Map) — `component/componentstatus/status.go:16`
- component -> pipeline (import; componentstatus.InstanceID encodes pipeline.ID) — `component/componentstatus/instance.go:12`
- component -> pdata (import componenttest.NewNopTelemetrySettings uses pcommon.NewResource) — `component/componenttest/nop_telemetry.go:12`

## Critical to know

- **Strict layered DAG.** `component` is the base layer — it is depended-ON by receiver/exporter/processor/connector/extension, not the reverse (`component/component.go:14`; non-test collector imports are only pdata+pipeline per `component/component.go:8`). `pdata` is the leaf/foundation: no production source imports receiver/processor/exporter/connector/service/otelcol/consumer/component (`pdata/go.mod:5-16`). `receiver` imports component/consumer/pdata/pipeline but NO processor/exporter/connector/service/otelcol, sitting strictly below them (`receiver/go.mod:5`).
- **The build manifest is the dependency-DAG source of truth.** Each component is its own Go module (go 1.25.0) wired to siblings via local `replace` directives (`receiver/go.mod:1,35`; `service/go.mod:1,149-262`). exporter/ alone ships 8 go.mod modules (`exporter/go.mod:1,60-118`); consumer/ ships 5 (`consumer/go.mod:1`).
- **Pipeline graph MUST be a DAG.** `service` builds it on the gonum graph library and fails with "cycle detected" via topo.DirectedCyclesIn, rendering the cycle starting from a connector (`service/internal/graph/graph.go:295,511`; built on gonum at `service/internal/graph/graph.go:24-26`).
- **Sealed factories everywhere.** Receiver/processor/exporter/connector Factory interfaces cannot be implemented directly — the unexported `unexportedFactoryFunc` marker forces construction through `NewFactory` (`receiver/receiver.go:58,90`; `processor/processor.go:49-51`; `exporter/exporter.go:47-50`; `connector/connector.go:79-80`).
- **Unsupported signals MUST return `pipeline.ErrSignalNotSupported`** — the default when no WithTraces/WithMetrics/WithLogs option is given (`receiver/receiver.go:146`; `exporter/exporter.go:135-138`; `processor/processor.go:131`).
- **Receive-then-acknowledge ordering invariant** (receiver): receive -> push via `nextConsumer.Consume*` -> only then ack/fail to the sender; storage-extension checkpoints stored only AFTER `Consume*` returns (`receiver/doc.go:23,32`).
- **Post-return ownership transfer** (consumer): after `Consume*` returns, the payload is no longer accessible — accessing it is undefined behavior (`consumer/logs.go:18`). A processor MUST NOT call the next component on error (`processor/processorhelper/traces.go:21`).
- **MutatesData copy-on-mutate contract.** A processor that modifies input MUST set `Capabilities.MutatesData=true` (default non-mutating via NewBaseImpl) (`consumer/internal/consumer.go:13,42`); the `service` capabilities node aggregates the flag across all processors + the exporter fanout so receivers know whether to clone (`service/internal/graph/graph.go:312-318`). Note processorhelper's own default is `MutatesData: true` (`processor/processorhelper/processor.go:69`).
- **pdata mutability invariant.** Every wrapper carries a `*State`; mutating methods call `AssertMutable` which panics "invalid access to shared data" when read-only; `MarkReadOnly` flips the bit (`pdata/internal/state.go:37,29`; `pdata/pcommon/map.go:40`). State also holds an atomic ref-count; a negative count panics "Cannot unref freed data" (`pdata/internal/state.go:53-69`).
- **A connector IS both an exporter and a receiver by interface composition** (consumer embedding), with NO edge to receiver/exporter/service/otelcol packages (`connector/connector.go:16-18,28-31`).
- **Experimental signals (Profiles) are segregated** into separate `x*` modules/packages that wrap the stable factory, keeping the stable interfaces signal-frozen (`receiver/xreceiver/receiver.go:30`; `processor/xprocessor/processor.go:32-36`; `exporter/xexporter/exporter.go:16-32`; `connector/xconnector/connector.go:19-20`; `consumer/xconsumer/go.mod:1`). Stable modules are v1.60.0, experimental/profile modules v0.154.0 (`consumer/go.mod:7` vs `consumer/xconsumer/go.mod:8`).
- **Tech choices:** Go multi-module (`go.mod:11`); gRPC+HTTP OTLP receiver, default endpoints gRPC localhost:4317 / HTTP localhost:4318 (`receiver/otlpreceiver/config.go:54`; `receiver/otlpreceiver/factory.go:44`); in-memory pdata (`consumer/traces.go:10`); cobra CLI, zap logging, confmap+koanf config, multierr (`otelcol/go.mod:1-3`, `otelcol/command.go:15`).
- **No persistent application store except the exporter send queue.** The exporter persistent queue is a durable FIFO backed by a `storage.Client` from a host-mediated storage extension (`exporter/exporterhelper/internal/queue/persistent_queue.go:50-72,549-560`); the default queue is in-memory (`exporter/exporterhelper/queue_batch.go:38-42`). All other component state is in-memory only.
<!-- DEEPINIT:END -->
