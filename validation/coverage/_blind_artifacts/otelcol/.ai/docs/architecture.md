<!--
provenance:
 stage: blind-mirror-test
 repo: otelcol@blind
 doc_in_inputs: false
 generated_by: DeepInit EMIT/GENERATE (blind artifact)
 inputs: source files + build manifests (go.mod) + directory layout ONLY
 date: 2026-06-13
-->

# Architecture — otelcol (blind re-derivation)

## Overview

otelcol is a Go multi-module project (`go.mod:11`) implementing an OpenTelemetry-style
telemetry collector. It is organized as a **strictly layered dependency DAG** whose
nodes are independently-versioned Go modules wired together by local `replace`
directives, so the **build manifest is the dependency-DAG source of truth**
(`receiver/go.mod:1,35`; `service/go.mod:1,149-262`).

Telemetry flows through a pipeline of pluggable components, each constructed through a
**sealed factory** keyed by `component.Type`. The collector's CLI layer (`otelcol`)
resolves configuration and drives the runtime orchestrator (`service`), which assembles
the in-memory pipeline graph from receiver/processor/exporter/connector/extension
components and owns their lifecycle.

## Layers (bottom to top)

1. **Foundation contracts**
 - `component` — defines the `Component` lifecycle interface (Start/Shutdown) that
 every receiver, exporter, processor, connector and extension must implement, plus
 the shared ID/Type/Kind/Config/Host/TelemetrySettings/BuildInfo contracts
 (`component/component.go:25`, `component/component.go:4`). It is the base layer:
 depended-ON by the pipeline modules, not the reverse
 (`component/component.go:14`).
 - `pdata` — the canonical in-memory data model for all pipeline signals
 (traces/metrics/logs/profiles + shared pcommon) with their proto/JSON
 (un)marshalers; "provides the data model definitions for all supported pipeline
 data" (`pdata/doc.go:6`). It is the leaf/foundation layer — no production source
 imports any pipeline component (`pdata/go.mod:5-16`).
 - `consumer` — defines the per-signal consumer interfaces
 (Traces/Metrics/Logs + experimental Profiles) that receive pipeline data, process
 it, and forward it on, plus the `BaseConsumer.Capabilities` contract; a
 contract/library package with no pipeline wiring of its own (`consumer/logs.go:15`).

2. **Pipeline component kinds**
 - `receiver` — pipeline ingress: defines the Traces/Metrics/Logs/Profiles
 interfaces + Factory, translates external-format data into internal pdata, and
 pushes it to the next consumer; ships the reference OTLP and nop receivers
 (`receiver/receiver.go:20`, `receiver/doc.go:6`).
 - `processor` — pipeline-middle: consumes one signal, optionally transforms it, and
 forwards it to the next consumer; each signal interface embeds
 `component.Component` plus the matching `consumer.*` (`processor/processor.go:16-31`).
 - `exporter` — egress: the terminal pipeline component that consumes telemetry and
 sends it to an external destination; each interface is a `component.Component` that
 also consumes the matching signal (`exporter/exporter.go:16-31`).
 - `connector` — bridges one source signal pipeline to one-or-more destination
 pipelines, simultaneously acting as an exporter from one pipeline and a receiver to
 downstream pipelines (`connector/connector.go:16-18`).

3. **Runtime orchestration**
 - `service` — runtime orchestrator: builds the internal telemetry providers
 (logger/meter/tracer), assembles the component pipeline DAG, and starts/stops/owns
 the lifecycle of all pipeline components and extensions; it is the concrete
 implementation of `component.Host` (`service/service.go:99`, `service/service.go:110`).
 - `otelcol` — CLI + lifecycle layer: handles the command-line, resolves
 configuration, and runs the collector via the `Collector` struct whose `Run` starts
 the collector and blocks until shutdown (`otelcol/collector.go:4-6`,
 `otelcol/collector.go:329`).

## Component decomposition rationale

The decomposition follows the **component-kind directory layout** of the repository
(receiver/, processor/, exporter/, connector/, service/, otelcol/, pdata/, consumer/,
component/), each kind grounded to its contract and version anchor:

- **receiver** (`receiver/`, anchor `versions.yaml:32`) — the ingress kind
 (`receiver/receiver.go:20`).
- **processor** (`processor/`, anchor `versions.yaml:31`) — the transform kind
 (`processor/processor.go:16-31`).
- **exporter** (`exporter/`, anchor `versions.yaml:27`) — the egress kind
 (`exporter/exporter.go:16-31`).
- **connector** (`connector/`, anchor `versions.yaml:53`) — joins pipelines
 (`connector/connector.go:16-18`).
- **service** (`service/`, anchor `service/service.go:43`) — the graph builder
 (`service/service.go:99`).
- **otelcol** (`otelcol/`, anchor `otelcol/collector.go:7`) — the Collector entry
 (`otelcol/collector.go:329`).
- **pdata** (`pdata/`, anchor `versions.yaml:10`) — the data model (`pdata/doc.go:6`).
- **consumer** (`consumer/`, anchor `consumer/consumer.go:4`) — the signal interfaces
 (`consumer/logs.go:15`).
- **component** (`component/`, anchor `component/component.go:25`) — the Component
 interface (`component/component.go:25`).

### Why these boundaries hold (structural evidence)

- **The DAG is acyclic and layered.** `component` is depended-ON only
 (`component/component.go:14`); `pdata` imports no pipeline component
 (`pdata/go.mod:5-16`); `receiver` imports component/consumer/pdata/pipeline but NOT
 processor/exporter/connector/service/otelcol (`receiver/go.mod:5`). The `service`
 pipeline graph itself MUST be a DAG — a cycle yields a "cycle detected" error via
 `topo.DirectedCyclesIn` (`service/internal/graph/graph.go:295,511`).
- **Sealed-factory construction** is uniform across the four pipeline kinds: each
 Factory carries an unexported `unexportedFactoryFunc` marker forcing construction
 through `NewFactory` (`receiver/receiver.go:58,90`; `processor/processor.go:49-51`;
 `exporter/exporter.go:47-50`; `connector/connector.go:79-80`).
- **A connector's exporter+receiver duality is expressed by interface composition**
 (consumer embedding), NOT by importing the receiver/exporter packages — there is no
 edge to receiver/exporter/service/otelcol from connector
 (`connector/connector.go:16-18,28-31`).
- **Experimental signals (Profiles) are segregated** into separate `x*`
 modules/packages that wrap the stable factory, keeping the stable interfaces
 signal-frozen (`receiver/xreceiver/receiver.go:30`; `processor/xprocessor/processor.go:32-36`;
 `exporter/xexporter/exporter.go:16-32`; `connector/xconnector/connector.go:19-20`;
 `consumer/xconsumer/go.mod:1`).

## Intra-pipeline data flow

Within a single pipeline the `service` graph enforces a strict order:
**receiver -> capabilities node -> processors (ordered) -> fanout node -> exporters**
(`service/internal/graph/graph.go:265-288`). A fanout node is ALWAYS inserted before
exporters, acting as a noop even with a single exporter
(`service/internal/graph/graph.go:280,128`). The capabilities node aggregates the
`MutatesData` flag across all processors + the exporter fanout so receivers know whether
to clone data (`service/internal/graph/graph.go:312-318`). Receiver and exporter nodes
are deduplicated across same-signal pipelines (node ID = pipeline-type + component-ID)
(`service/internal/graph/receiver.go:24`, `service/internal/graph/graph.go:215`).
