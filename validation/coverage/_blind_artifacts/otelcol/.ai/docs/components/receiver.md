<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND)
 component: receiver
 path: receiver/
 inputs: receiver/**/*.go, receiver/go.mod, receiver/metadata.yaml
 derived-from: source + build manifest only (prose docs removed per firewall)
 date: 2026-06-13
 rule: R1 — every claim grounded to file:line; omission over speculation
-->

# Component: receiver

The ingress edge of the collector pipeline: the module that defines the
`Traces` / `Metrics` / `Logs` (and experimental `Profiles`) receiver component
interfaces plus the `Factory` that constructs them, and ships the reference OTLP
and nop receiver implementations.

## Role

- Defines the receiver component contract — a receiver translates data from any
 external format into the collector's internal pdata format and pushes it to
 the next consumer; one signal-typed interface per telemetry signal (`Traces`,
 `Metrics`, `Logs`), each embedding `component.Component`. (`receiver/receiver.go:20`, `receiver/receiver.go:29`, `receiver/receiver.go:38`)
- Package contract: "A receiver receives data from a source (network or local
 scrape) and pushes the data to the pipelines it is attached to by calling the
 nextConsumer.Consume* function." (`receiver/doc.go:6`)
- Provides the `Factory` interface + `NewFactory` builder that produce signal
 receivers from a `component.Config` and a downstream `consumer`, gated by
 per-signal `StabilityLevel`. (`receiver/receiver.go:60`, `receiver/receiver.go:206`)

## Dependencies (edges)

- → component — every receiver interface embeds `component.Component`; `Factory`
 embeds `component.Factory`; `Settings` carries `component.ID` /
 `component.TelemetrySettings` / `component.BuildInfo`. (`receiver/receiver.go:21`, `receiver/receiver.go:61`, `receiver/receiver.go:45`)
- → consumer — factory create-funcs receive the downstream sink as a typed
 `consumer.Traces` / `consumer.Metrics` / `consumer.Logs` (`next`), the next
 pipeline node a receiver feeds. (`receiver/receiver.go:67`, `receiver/receiver.go:76`, `receiver/receiver.go:85`)
- → pipeline — unsupported signals return the sentinel
 `pipeline.ErrSignalNotSupported`; obsreport switches on `pipeline.Signal`. (`receiver/receiver.go:147`, `receiver/receiverhelper/obsreport.go:91`)
- → pdata (via otlpreceiver) — concrete OTLP receiver imports the otlp/grpc
 wire types `ptraceotlp` / `pmetricotlp` / `plogotlp` / `pprofileotlp` and
 registers gRPC servers for them. (`receiver/otlpreceiver/otlp.go:22`, `receiver/otlpreceiver/otlp.go:101`)
- → consumer/xconsumer — experimental Profiles signal feeds an
 `xconsumer.Profiles`. (`receiver/xreceiver/receiver.go:35`, `receiver/otlpreceiver/otlp.go:43`)
- → internal/componentalias — factory delegates component-type validation /
 deprecated type aliasing to `componentalias.ValidateComponentType` /
 `NewTypeAliasHolder`. (`receiver/receiver.go:150`, `receiver/receiver.go:210`)
- → consumer/consumererror (receiverhelper) — `consumererror.IsDownstream(err)`
 classifies an error as refused (downstream) vs failed (internal). (`receiver/receiverhelper/obsreport.go:188`)
- → internal/sharedcomponent (otlpreceiver) — the per-config singleton map that
 shares one `otlpReceiver` object across the trace/metric/log/profile create
 calls of the same config. (`receiver/otlpreceiver/factory.go:163`)
- → config/confighttp, config/configgrpc (otlpreceiver) — server transport
 construction for the OTLP HTTP and gRPC endpoints. (`receiver/otlpreceiver/otlp.go:18`, `receiver/otlpreceiver/factory.go:10`)
- Manifest build edges (local `replace` → sibling modules): component, consumer,
 consumer/consumertest, consumer/xconsumer, pdata, pdata/pprofile, pipeline,
 featuregate, internal/componentalias. (`receiver/go.mod:35-57`)
- NO edge to processor / exporter / connector / service / otelcol — none are in
 go.mod and none are imported anywhere under receiver/ (verified by an import
 sweep); receiver sits strictly below them in the layering. (`receiver/go.mod:5-33`)

## Data

- Owns no persistent data store. The only stateful structure is an in-process
 per-config singleton registry `receivers = sharedcomponent.NewMap[...]` that
 deduplicates `otlpReceiver` instances per `*Config`. (`receiver/otlpreceiver/factory.go:163`)
- Emits observability telemetry (not a store): per-signal accepted / refused /
 failed counters and a spec'd metric-key vocabulary
 (`accepted_spans`, `refused_spans`, `failed_spans`, …). (`receiver/receiverhelper/obsreport.go:256`, `receiver/receiverhelper/internal/obsmetrics.go:17`)
- Checkpoint/storage contract is documented as a receiver-side obligation, not
 owned here: receivers that checkpoint via a storage extension MUST store the
 checkpoint only AFTER `Consume*` returns. (`receiver/doc.go:32`)

## Boundary rules

- Receive-then-acknowledge ordering invariant: receive → push via
 `nextConsumer.Consume*` → only then acknowledge success / fail to the
 sender. (`receiver/doc.go:23`)
- `Factory` cannot be implemented directly — implementations MUST go through
 `NewFactory`, enforced by the unexported marker method `unexportedFactoryFunc`. (`receiver/receiver.go:58`, `receiver/receiver.go:90`)
- A receiver that does not support a signal MUST return
 `pipeline.ErrSignalNotSupported` from the corresponding Create func (default
 when no `WithTraces`/`WithMetrics`/`WithLogs` option was supplied). (`receiver/receiver.go:146`)
- `next` (the downstream consumer) is never nil — implementers may assume it. (`receiver/receiver.go:66`)
- Component-type/ID consistency is gate-checked on every create:
 `componentalias.ValidateComponentType(f, set.ID)`. (`receiver/receiver.go:150`)
- Error-to-source mapping is protocol-dependent: a transport must translate the
 Consume error into a protocol status (e.g. OTLP/HTTP status codes; gRPC maps
 non-permanent→Unavailable, permanent→InvalidArgument). (`receiver/doc.go:15`, `receiver/otlpreceiver/internal/trace/otlp.go:49`)

## Key facts

- Functional-options factory: `factory` holds per-signal create funcs +
 stability levels, set by `WithTraces`/`WithMetrics`/`WithLogs`; absent option
 ⇒ that signal returns ErrSignalNotSupported. (`receiver/receiver.go:115`, `receiver/receiver.go:182`)
- Experimental signals live in a separate decorator module `xreceiver`, whose
 `factory` embeds a `receiver.Factory` and adds `CreateProfiles`; the base
 factory stays signal-stable while Profiles evolves out-of-band. (`receiver/xreceiver/receiver.go:30`, `receiver/xreceiver/receiver.go:57`)
- OTLP receiver multiplexes 4 signals over 2 transports (gRPC + HTTP) from ONE
 shared instance; consumers are registered lazily via `registerXConsumer` and a
 server is only started for a signal whose `next` consumer is non-nil. (`receiver/otlpreceiver/otlp.go:100`, `receiver/otlpreceiver/factory.go:159`)
- Default OTLP endpoints: gRPC `localhost:4317`, HTTP `localhost:4318`; HTTP
 paths `/v1/traces`, `/v1/metrics`, `/v1/logs`, profiles `/v1development/profiles`. (`receiver/otlpreceiver/factory.go:44`, `receiver/otlpreceiver/factory.go:48`, `receiver/otlpreceiver/factory.go:23`)
- Error accounting is feature-gated: with `ReceiverhelperNewReceiverMetrics`
 enabled, downstream errors are counted as "refused" and internal errors as
 "failed" (+ an `otelcol_receiver_requests` outcome metric); gate disabled ⇒
 all errors counted as refused. (`receiver/receiverhelper/obsreport.go:187`, `receiver/receiverhelper/obsreport.go:204`)
- Long-lived-context handling: for stream/connection contexts obsreport starts
 the span from `context.Background` with a link to the connection context so
 the span ends at EndOp rather than living for the whole connection. (`receiver/receiverhelper/obsreport.go:154`)
- Public surface enforces non-trivial unkeyed-literal safety via a trailing
 `_ struct{}` field in `Settings` / `ObsReportSettings`. (`receiver/receiver.go:53`, `receiver/receiverhelper/obsreport.go:49`)
- Go multi-module: receiver is its own module `go.opentelemetry.io/collector/receiver`
 (go 1.25.0), wired to siblings by local `replace` directives — the build
 manifest is the dependency-DAG source of truth. (`receiver/go.mod:1`, `receiver/go.mod:35`)
<!-- DEEPINIT:END -->
