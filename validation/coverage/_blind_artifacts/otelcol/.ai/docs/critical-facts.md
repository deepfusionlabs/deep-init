<!--
provenance:
 stage: blind-mirror-test
 repo: otelcol@blind
 doc_in_inputs: false
 generated_by: DeepInit EMIT/GENERATE (blind artifact)
 inputs: source files + build manifests (go.mod) + directory layout ONLY
 date: 2026-06-13
-->

# Critical facts — otelcol (blind re-derivation)

The highest-value non-obvious invariants, boundary rules, and tech choices. Each is
grounded to a `file:line` opened in the blind tree.

## Tech choices

- **Go multi-module** project — each component is its own independently-versioned Go
 module (`go.mod:11`; `receiver/go.mod:1`; `service/go.mod:1`). exporter/ ships 8
 modules (`exporter/go.mod:1,60-118`), consumer/ ships 5
 (`consumer/go.mod:1`), component/ ships 3 (`component/go.mod:1`,
 `component/componentstatus/go.mod:1`, `component/componenttest/go.mod:1`), pdata is
 several modules (`pdata/pprofile/go.mod:1`, `pdata/xpdata/go.mod:1`). Modules are
 go 1.25.0 (`receiver/go.mod:1`, `connector/go.mod:3`).
- **gRPC + HTTP OTLP receiver** — the reference OTLP receiver multiplexes 4 signals
 over 2 transports from one shared instance (`receiver/otlpreceiver/config.go:54`;
 `receiver/otlpreceiver/otlp.go:100`). Default endpoints: gRPC localhost:4317 / HTTP
 localhost:4318; HTTP paths `/v1/traces`,`/v1/metrics`,`/v1/logs` and profiles
 `/v1development/profiles` (`receiver/otlpreceiver/factory.go:44`,
 `receiver/otlpreceiver/factory.go:23`).
- **In-memory pdata** as the universal signal carrier (`consumer/traces.go:10`;
 `pdata/doc.go:6`).
- **otelcol CLI/runtime stack:** cobra CLI, zap/zapcore logging, confmap+koanf config,
 multierr error accumulation (`otelcol/go.mod:1-3`, `otelcol/command.go:15`,
 `otelcol/collector.go:18-20`). The pipeline DAG is built on the gonum graph library
 (`service/internal/graph/graph.go:24-26`, `service/go.mod:65`). pdata uses
 json-iterator/go + google.golang.org/protobuf (`pdata/go.mod:6,14`) and
 google.golang.org/grpc for OTLP request/response types (`pdata/go.mod:13`).
- **Stability status:** package class `pkg`, distributions core+contrib; signals beta
 (metrics/traces/logs), profiles alpha (`otelcol/metadata.yaml:6-10`). pdata declares
 traces/metrics/logs stable (`pdata/metadata.yaml:11`). Stable consumer modules are
 v1.60.0, experimental/profile modules v0.154.0 (`consumer/go.mod:7` vs
 `consumer/xconsumer/go.mod:8`).

## Layering / boundary invariants

- **Build manifest is the dependency-DAG source of truth** — siblings are wired via
 local `replace` directives (`receiver/go.mod:1,35`; `service/go.mod:149-262`).
- **`component` is the base layer** — depended-ON by the pipeline modules, not the
 reverse; its only non-test collector imports are pdata + pipeline
 (`component/component.go:14`, `component/component.go:8`).
- **`pdata` is the leaf/foundation** — no production source imports
 receiver/processor/exporter/connector/service/otelcol/consumer/component
 (`pdata/go.mod:5-16`).
- **`receiver` sits strictly below** processor/exporter/connector/service/otelcol —
 none in its go.mod, none imported (`receiver/go.mod:5`).
- **A connector is both exporter and receiver by interface composition** (consumer
 embedding), with NO edge to receiver/exporter/service/otelcol
 (`connector/connector.go:16-18,28-31`).
- **Pipeline graph MUST be a DAG** — `topo.Sort` failure yields a "cycle detected"
 error via `topo.DirectedCyclesIn`; the cycle is always rendered starting from a
 connector (`service/internal/graph/graph.go:295,511`).
- **Strict layered intra-pipeline flow:** receiver -> capabilities node -> processors
 (ordered) -> fanout node -> exporters
 (`service/internal/graph/graph.go:265-288`); a fanout node is ALWAYS inserted before
 exporters even with a single exporter (`service/internal/graph/graph.go:280,128`).
- **`internal/` packages are import-restricted** to their module by Go's
 internal-package rule (`connector/internal/router.go:4`,
 `connector/internal/factory.go:4`); pdata's raw OTLP structs/codecs live under
 `pdata/internal`, exposed only via opaque value types
 (`pdata/pcommon/value.go:144`, `pdata/internal/wrapper_value.go:13-22`).

## Sealed-factory + signal contracts

- **Factories cannot be implemented directly** — an unexported
 `unexportedFactoryFunc` marker forces construction through `NewFactory`
 (`receiver/receiver.go:58,90`; `processor/processor.go:49-51,199`;
 `exporter/exporter.go:47-50,196-206`; `connector/connector.go:79-80,117,270`).
- **Component-type/ID consistency gate** is checked on every create via
 `componentalias.ValidateComponentType(f, set.ID)` (`receiver/receiver.go:150`;
 `processor/processor.go:134`; `exporter/exporter.go:140-142`;
 `connector/connector.go:238,313`).
- **Unsupported signals MUST return `pipeline.ErrSignalNotSupported`** — the default
 when no WithTraces/WithMetrics/WithLogs option is given
 (`receiver/receiver.go:146`; `processor/processor.go:131`;
 `exporter/exporter.go:135-138`). A connector's 9 (3x3) Create* signal-pair methods
 enforce only-supported conversions, else return `ErrDataTypes`/`ErrSignalNotSupported`
 (`connector/connector.go:93-103,308-311`).
- **Experimental signals (Profiles) are segregated** into separate `x*`
 modules/packages that wrap the stable factory, keeping it signal-frozen
 (`receiver/xreceiver/receiver.go:30`; `processor/xprocessor/processor.go:32-36`;
 `exporter/xexporter/exporter.go:16-32`; `connector/xconnector/connector.go:19-20`;
 `consumer/xconsumer/go.mod:1`).
- **Functional-options factory pattern** across the kinds: `NewFactory(type,
 defaultCfg,...FactoryOption)`; WithX options install a Create* func + StabilityLevel
 (`receiver/receiver.go:115,182`; `connector/connector.go:163-167,417-427`).
- **Public structs use the unkeyed-literal guard** — a trailing `_ struct{}` field
 forbids unkeyed-literal initialization (forward-compat)
 (`receiver/receiver.go:53`; `connector/connector.go:73-74`;
 `component/build_info.go:18`, `component/telemetry.go:32`).

## Data-flow / ownership invariants

- **Receive-then-acknowledge ordering** (receiver): receive -> push via
 `nextConsumer.Consume*` -> only then ack/fail to the sender
 (`receiver/doc.go:23`); receivers using a storage extension MUST store the checkpoint
 only AFTER `Consume*` returns (`receiver/doc.go:32`).
- **Post-return ownership transfer** (consumer): after `Consume*` returns, the payload
 is no longer accessible — accessing it is undefined behavior (`consumer/logs.go:18`).
- **A processor MUST NOT call the next component on error** — on error the returned data
 is ignored (`processor/processorhelper/traces.go:21`); `ErrSkipProcessingData` drops
 data WITHOUT propagating an error up the pipeline
 (`processor/processorhelper/processor.go:22`, `processor/processorhelper/traces.go:64`).
- **MutatesData copy-on-mutate contract:** a processor that modifies input MUST set
 `Capabilities.MutatesData=true`, else false; default non-mutating via `NewBaseImpl`
 (`consumer/internal/consumer.go:13,42`). The service capabilities node aggregates the
 flag across all processors + the exporter fanout so receivers know whether to clone
 (`service/internal/graph/graph.go:312-318`). Note processorhelper's own default
 capability is `MutatesData: true` (`processor/processorhelper/processor.go:69`).

## pdata data-model invariants

- **Mutability/shared-ownership invariant:** every wrapper carries a `*State`; mutating
 methods call `AssertMutable` which panics "invalid access to shared data" when
 read-only; `MarkReadOnly` flips the bit (`pdata/internal/state.go:37`,
 `pdata/pcommon/map.go:40`, `pdata/internal/state.go:29`, `pdata/plog/logs.go:7`).
- **Reference counting:** State holds an atomic ref-count; `Unref==true` means
 releasable, a negative count panics "Cannot unref freed data"
 (`pdata/internal/state.go:53-69`).
- **Machine-generated model:** generated via mdatagen
 (`//go:generate mdatagen metadata.yaml`, `pdata/doc.go:4`) — edit
 templates/metadata, not the hundreds of `generated_*` files under `pdata/internal`.
- **Hand-rolled codecs (not protobuf-go reflection):** custom varint encode
 (`pdata/internal/proto/marshal.go:7`) and a custom JSON iterator/stream
 (`pdata/internal/json/iterator.go`, `stream.go`) — a performance choice.
- **Value model** is a typed tagged-union over OTLP `AnyValue`: `ValueType` has 8
 variants Empty/Str/Int/Double/Bool/Map/Slice/Bytes; `Value` is pass-by-value over an
 internal pointer (`pdata/pcommon/value.go:18-28,54-58`).

## service lifecycle invariants

- **Lifecycle ordering is inverted vs topology:** start in REVERSE toposort order,
 shutdown in FORWARD toposort order (`service/internal/graph/graph.go:413,456`).
- **Fixed service start sequence:** start extensions -> NotifyConfig -> start pipelines
 -> NotifyPipelineReady; shutdown is the reverse (`service/service.go:234,268`).
- **Telemetry providers shut down in reverse creation order** (tracer, meter, logger)
 because tracer/meter may use the logger (`service/service.go:294`); Resource is
 created FIRST so logger/meter/tracer share one consistent `service.instance.id`
 (`service/service.go:132,135`).
- **Internal telemetry factory is mandatory** — `New` errors "telemetry factory not
 provided" if nil (`service/service.go:128`).
- **Validate is a config-only dry run** — builds the graph with noop providers and
 discards the result (`service/service.go:347,355`).
- **Fatal component status** (`StatusFatalError`) is pushed onto the host's
 `AsyncErrorChannel chan error` to signal the collector to abort
 (`service/internal/graph/host.go:84`, `service/service.go:78`).
- **Process metrics OS allow-list:** registered only on
 linux/darwin/windows/freebsd/openbsd/solaris/plan9; other OSes continue with a warning
 instead of failing (`service/service.go:380-393`).
- **Three feature gates govern behavior:** `service.AllowNoPipelines`,
 `service.profilesSupport`, `telemetry.newPipelineTelemetry`
 (`service/metadata.yaml:192-209`, `service/pipelines/config.go:29,33`).

## otelcol CLI / lifecycle invariants

- **Lifecycle state machine** Starting->Running->Closing->Closed stored atomically in
 `atomic.Int64` (`otelcol/collector.go:31-36,431`).
- **Single-select control loop** multiplexes config-watch reload, async fatal error, OS
 signals (SIGHUP=reload, SIGINT/SIGTERM=graceful shutdown), shutdown chan, ctx cancel
 (`otelcol/collector.go:376-407`); hot reload shuts down the old service and re-runs
 `setupConfigurationComponents` to build a fresh one (`otelcol/collector.go:266-276`).
- **Factory-mediated boundary:** otelcol references only Factory interfaces keyed by
 `component.Type`, never concrete impls (`otelcol/factories.go:21-54`).
- **Config-reference integrity gate:** every pipeline component reference and service
 extension must be a configured top-level component (`otelcol/config.go:82,90`); a
 connector ID may not collide with an exporter or receiver ID (`otelcol/config.go:68-78`);
 at least one receiver and one exporter required unless `AllowNoPipelines`
 (`otelcol/config.go:55-65`).
- **Redaction boundary:** print-config defaults to redacted; unredacted is explicit and
 feature-gated behind `otelcol.printInitialConfig` (`otelcol/command_print.go:40,141`).
- **Telemetry factory mandatory** — unmarshal fails fast with `errNilTelemetryFactory`
 if nil (`otelcol/unmarshaler.go:19,33`).
- **CLI is cobra-based** with subcommands featuregate/components/validate/print-config
 (`otelcol/command.go:25,44-47`); `--config` takes repeatable URIs and `--set` rewrites
 dotted keys to `::` YAML overrides with higher precedence (default scheme env)
 (`otelcol/flags.go:36-50`, `otelcol/command.go:65`).

## component contract invariants

- **`Config` is a bare alias `type Config any`** — no compile-time constraint; the
 struct/tag contract is enforced only at test time by reflection in
 `CheckConfigStruct` (`component/config.go:13`, `component/componenttest/configtest.go:39`).
- **Kind is a closed set of five sealed values** (Receiver/Processor/Exporter/Extension/
 Connector) using an unexported-field struct so callers cannot mint new kinds
 (`component/component.go:87,91`).
- **Component ID is the unique `type[/name]` key** (separator `/`); type regex
 `^[a-zA-Z][0-9a-zA-Z_]{0,62}$`, name 1–1024 Unicode chars excluding
 whitespace/control/symbol (`component/identifiable.go:15,22,27`).
- **Shutdown re-entrancy invariant:** MUST be safe to call without a prior `Start` and
 when already shut down (`component/component.go:48`); `StartFunc`/`ShutdownFunc`
 adapters are nil-safe (`component/component.go:65,69,79`).
- **Host-communication boundary:** a Component reaches its host only via the `Host`
 interface and must type-assert + error if a required extra interface is absent
 (`component/host.go:8,12`).
- **`componentstatus.InstanceID` encodes its pipeline IDs as a single 0x20-delimited
 string** specifically to stay Comparable / map-key usable
 (`component/componentstatus/instance.go:17,26`).

## doc.go provenance note

`receiver/doc.go` and `pdata/doc.go` are in-source package documentation (`.go` files),
not removed prose docs, so their stated contracts (receive-ack ordering,
checkpoint-after-Consume, protocol-dependent error mapping; the pdata data-model
definition) are code-grounded (`receiver/doc.go:4`, `pdata/doc.go:6`).
