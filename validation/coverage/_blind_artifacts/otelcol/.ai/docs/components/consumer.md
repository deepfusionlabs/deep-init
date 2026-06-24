<!-- DEEPINIT:START -->
<!--
provenance:
 stage: extract (BLIND)
 component: consumer
 run: p5-mirror-test
 inputs: C:/tmp/p5_otelcol_blind/consumer/ (source only; prose docs removed by firewall)
 date: 2026-06-13
-->

# Component: consumer

## Role

- Defines the per-signal **consumer interfaces** (`Traces`/`Metrics`/`Logs`) that receive pipeline data, process it, and pass it to the next node or destination, plus the `BaseConsumer.Capabilities` contract — it is interface/contract-only, with no pipeline wiring of its own. `consumer/logs.go:15`, `consumer/traces.go:15`, `consumer/metrics.go:15`, `consumer/doc.go:4`

## Dependencies (edges)

- → **pdata** — the signal interfaces are typed on the pdata payload types: `plog.Logs`, `ptrace.Traces`, `pmetric.Metrics`. `consumer/logs.go:10`, `consumer/traces.go:10`, `consumer/metrics.go:10`
- → **pdata** (module-level) — `go.opentelemetry.io/collector/pdata v1.60.0` is the sole non-test cross-component require, wired locally via `replace … =>../pdata`. `consumer/go.mod:7`, `consumer/go.mod:24`
- → **pdata/pprofile** — the experimental `xconsumer.Profiles` interface is typed on `pprofile.Profiles`. `consumer/xconsumer/profiles.go:12`, `consumer/xconsumer/go.mod:8`
- → **consumer** (self, subpackage edge) — `xconsumer` imports the parent `consumer` package for `consumer.Option` and the `internal` package for `BaseConsumer`/`NewBaseImpl`. `consumer/xconsumer/profiles.go:10`, `consumer/xconsumer/profiles.go:11`
- → **pdata** (consumererror) — `consumererror` and its `internal` helper type signal-error wrappers on `plog.Logs`/`pmetric.Metrics`/`ptrace.Traces`/`pprofile.Profiles`. `consumer/consumererror/signalerrors.go:8`, `consumer/consumererror/internal/retryable.go:7`
- → external **grpc** — `consumererror.Error` carries a `*grpc/status.Status` and maps OTLP gRPC/HTTP codes to retryability. `consumer/consumererror/error.go:11`, `consumer/consumererror/error.go:12`, `consumer/consumererror/go.mod:11`
- ← inbound (test-helper subpackage `consumertest`) — implements all four consumer interfaces, importing `consumer` + `xconsumer` + pdata; the `var _ consumer.Logs/Metrics/Traces` and `_ xconsumer.Profiles` static assertions prove conformance. `consumer/consumertest/consumer.go:9`, `consumer/consumertest/consumer.go:41`, `consumer/consumertest/go.mod:9`

## Data

- Owns **no persistence**. The only data-holding type is the test sink `consumertest.TracesSink`/`MetricsSink`/`LogsSink`/`ProfilesSink`, which buffers received payloads in-memory slices under a `sync.Mutex` for test assertions (not production state). `consumer/consumertest/sink.go:20`, `consumer/consumertest/sink.go:23`, `consumer/consumertest/sink.go:32`

## Boundary rules

- **MutatesData capability flag** — a processor whose `Consume*` modifies the input Traces/Logs/Metrics MUST set `Capabilities.MutatesData=true`; if it does not modify (or copies first) it MUST set false. This is the pipeline's copy-on-mutate contract. `consumer/internal/consumer.go:9`, `consumer/internal/consumer.go:13`
- **Default capability is non-mutating** — `NewBaseImpl` defaults `MutatesData:false`; `WithCapabilities` is the only override. `consumer/internal/consumer.go:42`, `consumer/consumer.go:22`
- **Post-return ownership transfer** — after `Consume*` returns, the payload is no longer accessible and accessing it is "undefined behavior" (the caller may reclaim/reuse it). `consumer/logs.go:18`, `consumer/traces.go:18`, `consumer/metrics.go:19`
- **Experimental signals quarantined** in a separate module/package `xconsumer` (Profiles), kept out of the stable `consumer` module. `consumer/xconsumer/profiles.go:4`, `consumer/xconsumer/go.mod:1`
- **Non-implementable convenience interface** — `consumertest.Consumer` carries an unexported `unexported` method so external packages cannot implement it, letting the project add methods without breaking compatibility. `consumer/consumertest/consumer.go:37`, `consumer/consumertest/consumer.go:62`
- **`NewDownstream` is internal-use-only** — explicitly "not intended to be used manually inside components"; it is for pipeline instrumentation to distinguish an internal failure from data refused further downstream. `consumer/consumererror/downstream.go:26`

## Key facts

- **Interface-over-func adapter pattern**: each signal exposes both an interface (`Logs`) and a func adapter (`ConsumeLogsFunc`) that satisfies it; `NewLogs/NewTraces/NewMetrics/NewProfiles` reject a nil func with `errNilFunc`. `consumer/logs.go:23`, `consumer/logs.go:37`, `consumer/consumer.go:15`, `consumer/xconsumer/profiles.go:15`
- **Type-alias re-export across the internal boundary**: `Capabilities` and `Option` in the public `consumer` package are Go type aliases (`=`) to `internal.*`, so the real definitions live in `consumer/internal` while staying API-compatible. `consumer/consumer.go:13`, `consumer/consumer.go:18`, `consumer/internal/consumer.go:7`
- **Functional-options construction**: `Option`/`OptionFunc` apply to a shared `BaseImpl`; `WithCapabilities` is the lone option. `consumer/internal/consumer.go:25`, `consumer/consumer.go:22`
- **OTLP error taxonomy** lives in `consumererror`: `permanent` (always-fails-on-same-input), `Error` (HTTP/gRPC status + retryable), and `downstreamError`; retryability is derived from specific OTLP HTTP codes (429/502/503/504) and gRPC codes (Canceled/DeadlineExceeded/Aborted/OutOfRange/Unavailable/DataLoss). `consumer/consumererror/permanent.go:10`, `consumer/consumererror/error.go:23`, `consumer/consumererror/error.go:44`, `consumer/consumererror/error.go:61`
- **Panic-on-success-code guard**: `NewOTLPHTTPError` panics on a 2xx code and `NewOTLPGRPCError` panics on `codes.OK` — success codes are reserved for future handling. `consumer/consumererror/error.go:40`, `consumer/consumererror/error.go:65`
- **Generic data-carrying retryable error**: `internal.Retryable[V]` is a Go generic constrained to the four pdata signal types, letting `consumererror.Traces/Logs/Metrics` (and `xconsumererror.Profiles`) carry the failed subset of data via `Data`. `consumer/consumererror/internal/retryable.go:13`, `consumer/consumererror/internal/retryable.go:29`, `consumer/consumererror/xconsumererror/signalerrors.go:13`
- **Multi-module layout**: this single directory tree ships **5 independent Go modules** — `consumer`, `consumer/xconsumer`, `consumer/consumererror`, `consumer/consumererror/xconsumererror`, `consumer/consumertest` — each with its own `go.mod` and local `replace` directives. `consumer/go.mod:1`, `consumer/xconsumer/go.mod:1`, `consumer/consumererror/go.mod:1`, `consumer/consumertest/go.mod:1`
- **Stable-vs-experimental version split** visible in versions: stable modules are `v1.60.0`; profile/experimental modules are `v0.154.0`. `consumer/go.mod:7`, `consumer/xconsumer/go.mod:8`
- **Component class is `pkg`** (a library package, not a runnable collector component like a receiver/exporter). `consumer/metadata.yaml:6`
<!-- DEEPINIT:END -->
