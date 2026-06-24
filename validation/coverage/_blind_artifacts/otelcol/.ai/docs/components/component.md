<!-- DEEPINIT:START -->
<!--
Provenance: stage=EXTRACT (BLIND) | component=component | path=component/
run=p5_otelcol_blind | inputs=component/*.go + go.mod manifests (no prose docs)
date=2026-06-13
-->

# component

## Role

- Defines the foundational abstraction layer for the Collector: the `Component` lifecycle interface (Start/Shutdown) that every receiver, exporter, processor, connector and extension must satisfy — `component/component.go:25`.
- The package self-describes its purpose as outlining "the abstraction of components within the OpenTelemetry Collector... the component lifecycle as well as defining the interface that components must fulfill" — `component/component.go:4`.

## Dependencies (edges)

- → **pdata** (`pdata/pcommon`): the root package's `TelemetrySettings.Resource` field is typed `pcommon.Resource` — `component/telemetry.go:11`, `component/telemetry.go:30`.
- → **pdata** (`pdata/pcommon`): declared as a direct require with a local `replace... =>../pdata` in the manifest — `component/go.mod:6`, `component/go.mod:30`.
- → **pdata** (`pdata/pcommon`): sub-package `componentstatus` imports `pcommon` for `Event.attributes pcommon.Map` — `component/componentstatus/status.go:16`, `component/componentstatus/status.go:89`.
- → **pipeline**: sub-package `componentstatus` imports `pipeline` for `InstanceID.pipelineIDs` / `NewInstanceID(... pipelineIDs...pipeline.ID)` — `component/componentstatus/instance.go:12`, `component/componentstatus/instance.go:30`.
- → **pdata** (`pdata/pcommon`): sub-package `componenttest` builds nop telemetry with `pcommon.NewResource` — `component/componenttest/nop_telemetry.go:12`, `component/componenttest/nop_telemetry.go:21`.
- (No outgoing edges to receiver / processor / exporter / connector / service / otelcol / consumer — this package is depended-on BY them, not the reverse; grep of non-test collector imports shows only pdata + pipeline — `component/component.go:8`.)

## Data

- Owns no persistence / data-store. The only state types are in-memory value structs: `BuildInfo` (`component/build_info.go:8`), `TelemetrySettings` (`component/telemetry.go:15`), and the `componentstatus.Event` carrying status/err/timestamp/attributes — `component/componentstatus/status.go:87`.

## Boundary rules

- Base layer of a layered architecture: the `Component` interface is the contract that "either a receiver, exporter, processor, connector, or an extension" must implement — `component/component.go:14`.
- `Shutdown` MUST be safe to call without a prior `Start`, and safe to call when already shut down — a documented re-entrancy invariant on the boundary — `component/component.go:48`.
- Host-communication boundary: a `Component` talks to its host only through the `Host` interface; the host may require additional interfaces and the component must type-assert and error if the assertion fails — `component/host.go:8`, `component/host.go:12`.
- Config-shape boundary: any `Config` implementation MUST pass `componenttest.CheckConfigStruct` (struct/pointer-to-struct, public fields carry a `mapstructure` tag) — `component/config.go:12`, `component/componenttest/configtest.go:23`.
- Sub-module `componentstatus` is explicitly experimental and "exempt from the Collector SIG's breaking change policy" — `component/componentstatus/status.go:7`.

## Key facts

- `Component` is split into separately-assignable `StartFunc` / `ShutdownFunc` func-types whose methods are nil-safe (return nil when the func is nil) — `component/component.go:65`, `component/component.go:69`, `component/component.go:79`.
- `Config` is a bare type alias `Config any` — no structural constraint at compile time; the contract is enforced at test time via reflection in `CheckConfigStruct` — `component/config.go:13`, `component/componenttest/configtest.go:39`.
- A component `ID` is the unique key `type[/name]` (separator `"/"`); type must match `^[a-zA-Z][0-9a-zA-Z_]{0,62}$`, name is 1–1024 Unicode chars excluding whitespace/control/symbol — `component/identifiable.go:15`, `component/identifiable.go:22`, `component/identifiable.go:27`.
- `Kind` is a closed set of five sealed values (Receiver/Processor/Exporter/Extension/Connector) implemented as an unexported-field struct so callers cannot construct new kinds — `component/component.go:87`, `component/component.go:91`.
- `StabilityLevel` is an ordered enum starting at 1 (0 = Undefined is skipped) with text (un)marshal + per-level log messages — `component/component.go:109`, `component/component.go:119`.
- This is a multi-module package: three independent Go modules live under `component/` — root `component`, `component/componentstatus`, `component/componenttest` — each with its own go.mod and local `replace` directives pointing at sibling modules — `component/go.mod:1`, `component/componentstatus/go.mod:1`, `component/componenttest/go.mod:1`.
- `componentstatus.InstanceID` encodes its pipeline IDs as a single delimited string (delimiter byte `0x20`) specifically so the struct stays Comparable (usable as a map key) — `component/componentstatus/instance.go:17`, `component/componentstatus/instance.go:26`.
- `componentstatus.Status` is an 8-value runtime health enum (None/Starting/OK/RecoverableError/PermanentError/FatalError/Stopping/Stopped); `ReportStatus` is best-effort — it type-asserts the host to `Reporter` and silently no-ops if unimplemented — `component/componentstatus/status.go:46`, `component/componentstatus/status.go:190`.
- Value structs `BuildInfo` and `TelemetrySettings` each carry a trailing `_ struct{}` field to forbid unkeyed literal initialization (forward-compat invariant) — `component/build_info.go:18`, `component/telemetry.go:32`.
- Telemetry plumbing depends on upstream OTel SDK only (`otel/metric`, `otel/trace`, `zap`), not on other collector modules — `component/telemetry.go:6`.
<!-- DEEPINIT:END -->
