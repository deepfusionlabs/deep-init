<!--
provenance:
 stage: blind-mirror-test
 repo: otelcol@blind
 doc_in_inputs: false
 generated_by: DeepInit EMIT/GENERATE (blind artifact)
 inputs: source files + build manifests (go.mod) + directory layout ONLY
 date: 2026-06-13
-->

# Technical dependencies — otelcol (blind re-derivation)

Every edge below is grounded to a `file:line` actually opened in the blind tree. Edge
`kind` distinguishes a Go source-level dependency (`import`, `interface-embed`,
`runtime-call`) from a build-manifest dependency (`project-ref` — a `require` + local
`replace` directive in a `go.mod`). The build manifest is the dependency-DAG source of
truth.

## receiver

- receiver -> component — import / interface-embed — `receiver/receiver.go:21`
- receiver -> consumer — import / runtime-call (next sink) — `receiver/receiver.go:67`
- receiver -> pipeline — import / sentinel-error + Signal switch — `receiver/receiver.go:147`
- receiver -> pdata — import (otlp wire types via otlpreceiver) — `receiver/otlpreceiver/otlp.go:22`
- receiver -> consumer — import xconsumer.Profiles (experimental signal) — `receiver/xreceiver/receiver.go:35`
- receiver -> component — project-ref (go.mod replace../component) — `receiver/go.mod:35`
- receiver -> consumer — project-ref (go.mod replace../consumer) — `receiver/go.mod:37`
- receiver -> pdata — project-ref (go.mod replace../pdata) — `receiver/go.mod:39`
- receiver -> pipeline — project-ref (go.mod replace../pipeline) — `receiver/go.mod:51`

## processor

- processor -> consumer — import / interface-embed — `processor/processor.go:10`, `processor/processor.go:16-31`
- processor -> consumer — runtime-call (next consumer forwarding target in Factory.Create*) — `processor/processor.go:58`, `processor/processor.go:67`, `processor/processor.go:76`
- processor -> component — import / interface-embed — `processor/processor.go:9`, `processor/processor.go:17`, `processor/processor.go:52`
- processor -> pipeline — import (ErrSignalNotSupported sentinel) — `processor/processor.go:12`, `processor/processor.go:131`
- processor -> consumer — import (consumer/xconsumer.Profiles in xprocessor) — `processor/xprocessor/processor.go:10`, `processor/xprocessor/processor.go:33-36`
- processor -> pdata — import (ptrace/pmetric/plog payload types in processorhelper + batchprocessor) — `processor/processorhelper/traces.go:15`, `processor/batchprocessor/batch_processor.go:23-25`
- processor -> consumer — import (consumer/consumererror permanent error in batchprocessor) — `processor/batchprocessor/batch_processor.go:22`
- processor -> component — import (client.Info/Metadata context for batch sharding) — `processor/batchprocessor/batch_processor.go:19`, `processor/batchprocessor/batch_processor.go:154-156`

## exporter

- exporter -> component — import / interface-embed / project-ref — `exporter/exporter.go:9,17`, `exporter/go.mod:7,60`
- exporter -> consumer — import / interface-embed (exporter IS a consumer) / project-ref — `exporter/exporter.go:10,18`, `exporter/exporterhelper/traces.go:21`, `exporter/go.mod:10,64`
- exporter -> pipeline — import / runtime-call (ErrSignalNotSupported, Signal key) / project-ref — `exporter/exporter.go:12,137`, `exporter/exporterhelper/internal/queue/persistent_queue.go:560`, `exporter/go.mod:15,74`
- exporter -> pdata — import / runtime-call (marshal ptrace/pmetric/plog/pprofile to OTLP) / project-ref — `exporter/otlpexporter/otlp.go:25-32,98`, `exporter/go.mod:14,68`
- exporter -> extension — runtime-call (host.GetExtensions -> storage.Extension -> storage.Client) / project-ref — `exporter/exporterhelper/internal/queue/persistent_queue.go:20,549-561`, `exporter/go.mod:42,66`
- exporter -> receiver — project-ref (local replace, build-graph edge) — `exporter/go.mod:76`, `exporter/exporterhelper/go.mod:66-67,93`
- exporter -> component — runtime-call (componentalias.ValidateComponentType before each Create) — `exporter/exporter.go:11,108,140`, `exporter/go.mod:116`

## connector

- connector -> consumer — import / interface-embed (connector interfaces embed consumer.Traces/Metrics/Logs; routers typed over consumer types) — `connector/connector.go:11,28-31`, `connector/logs_router.go:13`
- connector -> consumer — project-ref (go.mod require + replace../consumer) — `connector/go.mod:8,39`
- connector -> component — import / interface-embed (component.Component, component.Factory, component.ID/TelemetrySettings/BuildInfo) — `connector/connector.go:9,29,82,65-75`
- connector -> component — project-ref (go.mod require + replace../component) — `connector/go.mod:7,37`
- connector -> pdata — project-ref (go.mod require + replace../pdata; telemetry data model carried via consumers) — `connector/go.mod:12,41`
- connector -> pipeline — import / runtime-call (routers key by pipeline.ID; errors cite pipeline.Signal*/ErrSignalNotSupported) — `connector/logs_router.go:15,21`, `connector/connector.go:310`, `connector/internal/factory.go:14`
- connector -> pipeline — project-ref (go.mod require + replace../pipeline) — `connector/go.mod:14,51`
- connector -> internal/fanoutconsumer — import / runtime-call (routers build fan-out via fanoutconsumer.NewLogs/NewMetrics/NewTraces) — `connector/logs_router.go:14,37`, `connector/go.mod:11,55`
- connector -> internal/componentalias — import / runtime-call (TypeAliasHolder + ValidateComponentType in every Create*) — `connector/connector.go:12,238,313`, `connector/go.mod:10,53`
- connector -> consumer/xconsumer — import (xconnector profiles surface typed over xconsumer.Profiles) — `connector/xconnector/connector.go:13,55`, `connector/go.mod:27,47`
- connector -> pipeline/xpipeline — import (xconnector error paths cite xpipeline.SignalProfiles) — `connector/xconnector/connector.go:16,274`

## service

- service -> receiver — import — `service/service.go:26`
- service -> processor — import — `service/service.go:25`
- service -> exporter — import — `service/service.go:22`
- service -> connector — import — `service/service.go:21`
- service -> extension — import — `service/service.go:23`
- service -> component — import + runtime-call (node.(component.Component).Start/Shutdown) — `service/internal/graph/graph.go:417`
- service -> consumer — import + runtime-wiring (consumer.Traces/Metrics/Logs + Capabilities) — `service/internal/graph/graph.go:312`
- service -> pdata — import (pcommon.NewResource) — `service/service.go:24`
- service -> otelcol — project-ref (go.mod require + local replace../otelcol; no source import in this component) — `service/go.mod:241`

## otelcol

- otelcol -> service — runtime-call — `otelcol/collector.go:212`
- otelcol -> service — import — `otelcol/collector.go:25`
- otelcol -> component — import — `otelcol/factories.go:9`
- otelcol -> receiver — import — `otelcol/factories.go:15`
- otelcol -> processor — import — `otelcol/factories.go:14`
- otelcol -> exporter — import — `otelcol/factories.go:11`
- otelcol -> extension — import — `otelcol/factories.go:12`
- otelcol -> connector — import — `otelcol/factories.go:10`
- otelcol -> consumer — project-ref — `otelcol/go.mod:20`
- otelcol -> pdata — project-ref — `otelcol/go.mod:94`

## pdata

- pdata -> featuregate — import (registers pdata.useProtoPooling) — `pdata/internal/metadata/generated_feature_gates.go:6` (registers `pdata.useProtoPooling` at `:9`); manifest replace at `pdata/go.mod:36`
- pdata -> client — import (xpdata sub-module only, not root) — `pdata/xpdata/request/context.go:11`; required at `pdata/xpdata/go.mod:8` with replace =>../../client

## consumer

- consumer -> pdata — import (signal payload types plog.Logs/ptrace.Traces/pmetric.Metrics) — `consumer/logs.go:10`
- consumer -> pdata — project-ref (go.mod require + local replace../pdata) — `consumer/go.mod:7`
- consumer -> pdata — import (pprofile.Profiles for experimental xconsumer.Profiles) — `consumer/xconsumer/profiles.go:12`
- consumer -> consumer — import (xconsumer subpackage imports parent consumer.Option + internal) — `consumer/xconsumer/profiles.go:10`
- consumer -> pdata — import (consumererror signal-error wrappers on plog/pmetric/ptrace/pprofile) — `consumer/consumererror/internal/retryable.go:7`

## component

- component -> pdata — import (pcommon type-ref: TelemetrySettings.Resource pcommon.Resource) — `component/telemetry.go:11`
- component -> pdata — project-ref (direct require + replace =>../pdata) — `component/go.mod:6`
- component -> pdata — import (componentstatus: Event.attributes pcommon.Map) — `component/componentstatus/status.go:16`
- component -> pipeline — import (componentstatus.InstanceID encodes pipeline.ID; NewInstanceID takes pipeline.ID) — `component/componentstatus/instance.go:12`
- component -> pdata — import (componenttest.NewNopTelemetrySettings uses pcommon.NewResource) — `component/componenttest/nop_telemetry.go:12`

## Layering notes (boundary evidence)

- `component` is the base layer — depended-ON, not depending: its only non-test
 collector imports are pdata + pipeline (`component/component.go:8`, `component/component.go:14`).
- `pdata` is the leaf/foundation — no production import of receiver/processor/exporter/
 connector/service/otelcol/consumer/component (`pdata/go.mod:5-16`).
- `receiver` sits strictly below processor/exporter/connector/service/otelcol — none
 appear in its go.mod and none are imported (`receiver/go.mod:5`).
- `connector` has NO edge to receiver/exporter/service/otelcol; its exporter+receiver
 duality is interface composition only (`connector/connector.go:16-18,28-31`).
- `service` requires `otelcol` only as a build-manifest project-ref (replace
../otelcol) with no source import in the component (`service/go.mod:241`).
