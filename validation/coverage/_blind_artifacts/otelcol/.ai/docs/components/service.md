<!-- Provenance: DeepInit EXTRACT stage (BLIND, code-only re-derivation) | component=service | path=service/ | derived from source + go.mod | date=2026-06-13 -->

# Component: service

## Role

- The runtime orchestrator that assembles a Collector's telemetry providers, builds the component pipeline DAG, and starts/stops/owns the lifecycle of all pipeline components and extensions; it is the concrete implementation of `component.Host` — `service/service.go:99` ("// Service represents the implementation of a component.Host"), `service/service.go:110` (`New creates a new Service, its telemetry, and Components`).

## Dependencies (edges)

- Depends on **receiver**: imports `go.opentelemetry.io/collector/receiver` and stores `ReceiversFactories map[component.Type]receiver.Factory` in Settings — `service/service.go:26`, `service/service.go:53`.
- Depends on **processor**: imports `go.opentelemetry.io/collector/processor`, `ProcessorsFactories map[component.Type]processor.Factory` — `service/service.go:25`, `service/service.go:57`.
- Depends on **exporter**: imports `go.opentelemetry.io/collector/exporter`, `ExportersFactories map[component.Type]exporter.Factory` — `service/service.go:22`, `service/service.go:61`.
- Depends on **connector**: imports `go.opentelemetry.io/collector/connector`, `ConnectorsFactories map[component.Type]connector.Factory` — `service/service.go:21`, `service/service.go:65`.
- Depends on **extension**: imports `go.opentelemetry.io/collector/extension`, `ExtensionsFactories map[component.Type]extension.Factory` — `service/service.go:23`, `service/service.go:72`.
- Depends on **component**: imports `go.opentelemetry.io/collector/component` (BuildInfo, ID, Config, TelemetrySettings, Host, Kind) — `service/service.go:19`; the graph reverse-toposort casts nodes to `component.Component` and calls `Start`/`Shutdown` — `service/internal/graph/graph.go:417`, `service/internal/graph/graph.go:463`.
- Depends on **consumer**: the internal graph imports `go.opentelemetry.io/collector/consumer` and `consumer/xconsumer` and wires each node's `consumer.Traces/Metrics/Logs` (+ `xconsumer.Profiles`) plus `consumer.Capabilities{MutatesData}` — `service/internal/graph/graph.go:32`, `service/internal/graph/graph.go:312`, `service/internal/graph/consumer.go:7`.
- Depends on **pdata**: imports `go.opentelemetry.io/collector/pdata/pcommon` to build the empty resource for `Validate` — `service/service.go:24`, `service/service.go:353` (`pcommon.NewResource`).
- Depends on **otelcol**: the module requires `go.opentelemetry.io/collector/otelcol v0.154.0` with a local `replace... =>../otelcol` (build-manifest edge; no non-test source import of otelcol was found in this component) — `service/go.mod:38`, `service/go.mod:241`.
- Depends on **confmap** (config substrate): `CollectorConf *confmap.Conf`, and extensions are notified with a cloned `confmap.Conf` — `service/service.go:20`, `service/service.go:49`, `service/extensions/extensions.go:123`.
- Depends on **pipeline** (signal/ID types): the graph keys nodes by `pipeline.ID`/`pipeline.Signal` and switches on `SignalTraces/Metrics/Logs` + `xpipeline.SignalProfiles` — `service/internal/graph/graph.go:35`, `service/internal/graph/graph.go:320`.
- Internal dependency on `internal/graph`: `Service.host` holds a `*graph.Host`, and `initGraph` calls `graph.Build(...)` to construct the pipeline DAG — `service/service.go:103`, `service/service.go:326`.
- Internal dependency on `internal/builders`: builders wrap the per-kind factory maps (`builders.NewReceiver/NewProcessor/NewExporter/NewConnector/NewExtension`) — `service/service.go:115`, `service/service.go:28`.
- Internal dependency on `service/telemetry`: the `telemetry.Factory` creates the resource, logger, meter provider, and tracer provider — `service/service.go:34`, `service/service.go:96`, `service/service.go:135`.

## Data

- Owns no persistent data store; it is an in-memory runtime. The only durable-ish state is the in-memory pipeline DAG `componentGraph *simple.DirectedGraph` (gonum) plus the `pipelines map[pipeline.ID]*pipelineNodes` and `instanceIDs map[int64]*componentstatus.InstanceID` maps — `service/internal/graph/graph.go:62`, `service/internal/graph/graph.go:65`, `service/internal/graph/graph.go:68`.
- Reads the collector configuration object (`confmap.Conf`) in memory; it does not read it from disk itself (config loading is upstream) — `service/service.go:48`, `service/service.go:125`.
- Emits internal process/runtime metrics (e.g. `process_cpu_seconds`, `process_memory_rss`, `process_uptime`) and per-component item/size counters as telemetry output, not stored — `service/metadata.yaml:74`, `service/metadata.yaml:121`, `service/metadata.yaml:171`.

## Boundary rules

- The pipeline graph MUST be a DAG: `buildComponents` runs `topo.Sort` and on failure returns a "cycle detected" error built from `topo.DirectedCyclesIn`; a reported cycle is always rendered starting from a connector — `service/internal/graph/graph.go:295`, `service/internal/graph/graph.go:511`, `service/internal/graph/graph.go:526`.
- Strict layered data-flow per pipeline: receiver -> capabilities node -> processors (in order) -> fanout node -> exporters; edges are drawn only in that direction — `service/internal/graph/graph.go:265`–`service/internal/graph/graph.go:288`.
- Start/stop ordering is inverted vs. topology: components start in REVERSE topological order (downstream consumer ready first) and shut down in FORWARD topological order (upstream drains first) — `service/internal/graph/graph.go:413`, `service/internal/graph/graph.go:456`.
- Service-level start sequence is fixed: start extensions -> NotifyConfig -> start pipelines -> NotifyPipelineReady; shutdown is the reverse: NotifyPipelineNotReady -> shutdown pipelines -> shutdown extensions -> shutdown telemetry — `service/service.go:234`, `service/service.go:268`.
- Telemetry providers are shut down in reverse order of creation (tracer, then meter, then logger) because tracer/meter may use the logger — `service/service.go:294`.
- The "x" (experimental) variants are accessed only via interface type-assertion: profiles support requires a node's factory to satisfy `xconnector.Factory`, else stability is `Undefined` — `service/internal/graph/graph.go:562`, `service/internal/graph/graph.go:599`.
- Connector cross-pipeline validity is enforced: a connector used as exporter must have a supported corresponding receiver use (and vice-versa) or `createNodes` errors out — `service/internal/graph/graph.go:173`, `service/internal/graph/graph.go:179`.

## Key facts

- Multi-module Go: `service` is its own module `go.opentelemetry.io/collector/service` (go 1.25.0) that wires the sibling component modules together via local `replace` directives (`../receiver`, `../processor`, `../exporter`, `../connector`, `../extension`, `../consumer`, `../pdata`, `../component`, `../otelcol`,...) — `service/go.mod:1`, `service/go.mod:3`, `service/go.mod:149`–`service/go.mod:262`.
- The pipeline DAG is built on the gonum graph library (`gonum.org/v1/gonum/graph/simple` + `/topo`), not a hand-rolled graph — `service/internal/graph/graph.go:24`–`service/internal/graph/graph.go:26`, `service/go.mod:65`.
- A capabilities node aggregates the `MutatesData` flag across all processors and the exporter fanout so receivers know whether they must clone data — `service/internal/graph/graph.go:312`–`service/internal/graph/graph.go:318`, `service/internal/graph/graph.go:293` (comment).
- Receiver and exporter nodes are DEDUPLICATED across pipelines of the same signal type (node ID derived from "pipeline type" + "component ID"); a re-seen node just records the extra pipeline via `instanceID.WithPipelines` — `service/internal/graph/receiver.go:24`, `service/internal/graph/graph.go:215`, `service/internal/graph/graph.go:238`.
- A fanout node is ALWAYS inserted before exporters, acting as a noop even with a single exporter — `service/internal/graph/graph.go:280` (comment), `service/internal/graph/graph.go:128`.
- The internal telemetry factory is mandatory: `New` returns `errors.New("telemetry factory not provided")` if `Settings.TelemetryFactory` is nil — `service/service.go:128`.
- Resource is created FIRST so logger/meter/tracer share one resource with a consistent `service.instance.id` — `service/service.go:132` (comment), `service/service.go:135`.
- `Validate` is a config-only dry run: it builds the graph with noop logger/tracer/meter providers (`zap.NewNop`, `nooptrace`, `noopmetric`) and discards the result — `service/service.go:347`, `service/service.go:349`–`service/service.go:354`.
- The Service implements `component.Host` via the embedded `graph.Host`, which also satisfies `hostcapabilities.ModuleInfo`, `ExposeExporters` (deprecated), and `ComponentFactory` — `service/internal/graph/host.go:24`–`service/internal/graph/host.go:29`, `service/hostcapabilities/interfaces.go:16`.
- Process metrics are registered only on an allow-list of OSes (linux, darwin, windows, freebsd, openbsd, solaris, plan9); on others startup continues with a warning instead of failing — `service/service.go:380`–`service/service.go:393`.
- Three feature gates govern behavior: `service.AllowNoPipelines`, `service.profilesSupport`, `telemetry.newPipelineTelemetry` — `service/metadata.yaml:192`, `service/metadata.yaml:198`, `service/metadata.yaml:204`; pipeline-count and profiles-signal validation are gated on the first two — `service/pipelines/config.go:29`, `service/pipelines/config.go:33`.
- Extension start order is computed (dependency-ordered) and stop order is its reverse (`slices.Backward`) — `service/extensions/extensions.go:35`, `service/extensions/extensions.go:71`, `service/extensions/extensions.go:233`.
- Fatal component status (`StatusFatalError`) is pushed onto the host's `AsyncErrorChannel chan error` to signal the collector to abort — `service/internal/graph/host.go:84`, `service/service.go:78`.
- Serves zPages debug HTTP endpoints (servicez, pipelinez, extensionz, featurez) registered on an http.ServeMux — `service/internal/graph/host.go:89`–`service/internal/graph/host.go:114`.
