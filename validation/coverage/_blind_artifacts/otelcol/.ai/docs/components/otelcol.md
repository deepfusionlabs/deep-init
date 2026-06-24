<!-- DEEPINIT:START -->
<!--
provenance: stage=extract component=otelcol run=p5-blind inputs=otelcol/ date=2026-06-13
NOTE: derived BLIND from source only (prose architecture docs removed). Every claim cites file:line.
module: go.opentelemetry.io/collector/otelcol (otelcol/go.mod:1)
-->

# Component: otelcol

## Role

- The collector's CLI + lifecycle layer: handles command-line, configuration resolution, and runs the OpenTelemetry Collector via the `Collector` struct and `NewCollector` constructor — `(Collector).Run` starts the collector and blocks until shutdown (otelcol/collector.go:4-6, otelcol/collector.go:329).

## Dependencies (edges)

- **→ service**: imports `go.opentelemetry.io/collector/service`; constructs and owns the running service via `service.New(...)`, passing per-kind configs + factories, then `Start`/`Shutdown` it (otelcol/collector.go:25, otelcol/collector.go:212, otelcol/collector.go:258, otelcol/collector.go:421).
- **→ service** (validate path): `service.Validate(...)` for the dry-run/validate flow (otelcol/collector.go:296).
- **→ service/pipelines**: imports for the `AllowNoPipelines` feature-gate check during config validation (otelcol/config.go:12, otelcol/config.go:57).
- **→ component**: imports `go.opentelemetry.io/collector/component`; uses `component.BuildInfo`, `component.Type`, `component.ID`, `component.Config`, `component.Factory` throughout the config + factory model (otelcol/factories.go:9, otelcol/factories.go:23, otelcol/config.go:24).
- **→ receiver**: imports; `Factories.Receivers map[component.Type]receiver.Factory` (otelcol/factories.go:15, otelcol/factories.go:23).
- **→ processor**: imports; `Factories.Processors map[component.Type]processor.Factory` (otelcol/factories.go:14, otelcol/factories.go:26).
- **→ exporter**: imports; `Factories.Exporters map[component.Type]exporter.Factory` (otelcol/factories.go:11, otelcol/factories.go:29).
- **→ extension**: imports; `Factories.Extensions map[component.Type]extension.Factory` (otelcol/factories.go:12, otelcol/factories.go:32).
- **→ connector**: imports; `Factories.Connectors map[component.Type]connector.Factory` (otelcol/factories.go:10, otelcol/factories.go:35).
- **→ consumer**: declared in the manifest require block (otelcol/go.mod:20) — transitive via the service/pipeline graph; not directly imported in the top-level package files read.
- **→ pdata**: declared in the manifest as an indirect require (otelcol/go.mod:94) — used transitively via service/consumer, not directly imported here.
- **→ service/telemetry**: imports for `Factories.Telemetry telemetry.Factory` (otelcol/factories.go:16, otelcol/factories.go:38); nil-telemetry is a hard error (otelcol/unmarshaler.go:19, otelcol/unmarshaler.go:33).
- **→ confmap**: imports; config resolution via `confmap.Resolver`, `confmap.Validate`, `confmap.New.Marshal` (otelcol/collector.go:23, otelcol/configprovider.go:24, otelcol/collector.go:191).
- **→ featuregate**: imports; the `featuregate` subcommand + global registry flag wiring (otelcol/command.go:17, otelcol/command.go:26).
- **→ internal/configunmarshaler** (own internal): generic per-kind config unmarshalling `Configs[F component.Factory]` (otelcol/unmarshaler.go:13, otelcol/internal/configunmarshaler/configs.go:16).
- **→ internal/grpclog** (own internal): installs the collector's zap logger as the gRPC logger (otelcol/collector.go:24, otelcol/collector.go:255).
- **→ internal/componentalias**: deprecated-alias resolution in `MakeFactoryMap` (otelcol/factories.go:13, otelcol/factories.go:68).

## Data

- **No persistence / DB owned.** This component owns no datastore; its only "stores" are in-memory and the config source.
- **In-memory log buffer**: `bufferedCore` buffers zap log entries before the real service logger exists, then they are drained via `TakeLogs` once (otelcol/buffered_core.go:26, otelcol/buffered_core.go:71, otelcol/collector.go:245).
- **Config source (read-only)**: configuration is *resolved* (read) from URIs via the `confmap.Resolver` behind `ConfigProvider`; it is read, watched, and re-read on change — never written back (otelcol/configprovider.go:24, otelcol/configprovider.go:55, otelcol/configprovider.go:83).

## Boundary rules

- **Factory-mediated boundary**: this layer never references concrete receiver/processor/exporter/connector/extension implementations — only their `Factory` interfaces keyed by `component.Type` in the `Factories` struct (otelcol/factories.go:21-54).
- **Config-reference integrity gate**: `Config.Validate` enforces cross-references — every pipeline receiver/processor/exporter and every service extension must be a configured top-level component (otelcol/config.go:82, otelcol/config.go:90).
- **Connector ID disambiguation**: a connector ID may not collide with an exporter or receiver ID (otelcol/config.go:68-78).
- **Redaction boundary**: `print-config` defaults to `redacted` mode; `unredacted` must be explicitly requested and is gated behind the `otelcol.printInitialConfig` feature gate (otelcol/command_print.go:40, otelcol/command_print.go:57, otelcol/command_print.go:141).
- **No-default-component rule**: there is no default receiver or exporter; config must specify at least one of each unless `AllowNoPipelines` is enabled (otelcol/config.go:55-65).

## Key facts

- **Lifecycle state machine**: `State` = Starting → Running → Closing → Closed, stored atomically (`atomic.Int64`) (otelcol/collector.go:31-36, otelcol/collector.go:106, otelcol/collector.go:431).
- **Control loop** multiplexes config-watch reloads, async fatal errors, OS signals, shutdown, and ctx-cancel in one `select`; SIGHUP triggers reload, SIGINT/SIGTERM trigger graceful shutdown (otelcol/collector.go:376-407).
- **Hot config reload**: on a watch event, `reloadConfiguration` shuts down the old service and re-runs `setupConfigurationComponents` to build a fresh service (otelcol/collector.go:266, otelcol/collector.go:274).
- **CLI surface (cobra)**: root command + subcommands `featuregate`, `components`, `validate`, `print-config` (otelcol/command.go:25, otelcol/command.go:44-47).
- **`--config` and `--set` flags**: `--config` accepts repeatable URIs; `--set` rewrites dotted keys to `::` YAML overrides with higher precedence; default scheme is `env` (otelcol/flags.go:36, otelcol/flags.go:39-50, otelcol/command.go:65).
- **Telemetry factory is mandatory**: unmarshalling fails fast with `errNilTelemetryFactory` if `Factories.Telemetry` is nil (otelcol/unmarshaler.go:19, otelcol/unmarshaler.go:33).
- **Two-phase logging via swappable zap core**: a `bufferedCore` captures early logs, wrapped by a `collectorCore` whose delegate is hot-swapped (`atomic.Pointer`) to the real service logger once it exists (otelcol/collector.go:125-128, otelcol/collector_core.go:14-16, otelcol/collector.go:242).
- **Generic config unmarshalling**: `configunmarshaler.Configs[F]` creates each component's default config then unmarshals user overrides on top, erroring on unknown component types (with a special hint that `logging` exporter is removed → use `debug`) (otelcol/internal/configunmarshaler/configs.go:49-57, otelcol/internal/configunmarshaler/configs.go:67-72).
- **Module-info plumbing**: builder module refs per component kind are threaded into `service.ModuleInfos` for the `components` subcommand / build provenance (otelcol/collector.go:168, otelcol/collector.go:227-233).
- **gRPC log noise control**: gRPC logger is clamped to WARN when collector level is INFO, and a `fixedVerbosityLogger` corrects zapgrpc's verbosity-vs-severity conflation (otelcol/internal/grpclog/logger.go:24-31, otelcol/internal/grpclog/logger.go:41-43).
- **Tech choices**: Go 1.25 multi-module (own go.mod), cobra for CLI, zap/zapcore for logging, confmap+koanf for config, multierr for error accumulation (otelcol/go.mod:1-3, otelcol/command.go:15, otelcol/collector.go:18-20).
- **Status/stability**: package class `pkg`, distributions core+contrib; signals beta (metrics/traces/logs), profiles alpha (otelcol/metadata.yaml:6-10).
<!-- DEEPINIT:END -->
