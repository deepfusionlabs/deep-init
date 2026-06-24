<!-- DeepInit horizontal | Component: system-wide
Run ID: blind-eabe-2026-06-13
Input files processed: all *.csproj, Directory.Build.props, Directory.Packages.props, Program.cs (x4), Module.cs, AppHost/Program.cs (x2), Dockerfile (x2), appsettings*.json
Generated: 2026-06-13 -->

# Technical Dependencies & Cascade Risk

## System shape

Two **independently deployable.NET 10 / C# applications** plus a shared NuGet library set:

1. **Fitnet** — a **modular monolith** (`Fitnet/Src`). One ASP.NET Core host (`Fitnet/Src/Fitnet`) composing three feature modules (Offers, Passes, Reports) that each own a PostgreSQL schema in one shared database. — `Fitnet/Src/Fitnet/Program.cs:16-18`.
2. **Fitnet.Contracts** — an **extracted microservice** (`Fitnet.Contracts/Src`), Clean/Onion architecture (Core / Application / Infrastructure / Api), its own host, its own PostgreSQL database. — `Fitnet.Contracts/Src/Fitnet.Contracts/Program.cs:13`.
3. **Fitnet.Common** — five **shared libraries published as NuGet packages** (`EvolutionaryArchitecture.Fitnet.Common.*`, version `4.2.0`) consumed by BOTH apps. — `Fitnet.Common/Directory.Build.props:15`; consumed e.g. `Fitnet/Src/Directory.Packages.props:9-11`.

Each app has an **Aspire AppHost** orchestrator (Postgres + RabbitMQ) for local run. — `Fitnet/Src/AppHost/Program.cs:5-19`, `Fitnet.Contracts/Src/AppHost/Program.cs:5-19`.

## The two coupling mechanisms (this is the key to the dependency graph)

The build graph uses TWO distinct mechanisms — confusing them mis-reads the architecture:

- **`ProjectReference`** (in-solution, compile-time) — used WITHIN a deployable unit.
- **`PackageReference`** (versioned NuGet package) — used to consume `Fitnet.Common.*` and the `Fitnet.Contracts.IntegrationEvents` public event contract. The monolith depends on the microservice's events as a **package**, not a project. — `Fitnet/Src/Passes/Fitnet.Passes.Api/Fitnet.Passes.Api.csproj:18` (`EvolutionaryArchitecture.Fitnet.Contracts.IntegrationEvents`).

`Fitnet.Common.*` references in feature modules are **PackageReference**, so the Common source tree (`Fitnet.Common/`) is NOT in either app's project graph — it is pre-built and pulled from a GitHub NuGet feed. — `Fitnet/Src/Dockerfile:11` (`dotnet nuget add source … nuget.pkg.github.com/evolutionary-architecture`).

## ProjectReference edges (compile-time, intra-app)

**Fitnet monolith** (`Fitnet/Src`):
- `Fitnet` (host) → `Offers.Api`, `Passes.Api`, `Reports` — `Fitnet/Src/Fitnet/Fitnet.csproj:16-18`.
- `Offers.Api` → `Passes.IntegrationEvents`, `Offers.DataAccess` — `Fitnet/Src/Offers/Fitnet.Offers.Api/Fitnet.Offers.Api.csproj:8-9`. **[cross-module edge — see below]**
- `Passes.Api` → `Passes.DataAccess`, `Passes.IntegrationEvents` — `Fitnet/Src/Passes/Fitnet.Passes.Api/Fitnet.Passes.Api.csproj:4-5`.
- `Reports` → (no project refs; reads other modules' data via raw SQL — see data-layer.md).

**Fitnet.Contracts microservice** (`Fitnet.Contracts/Src`):
- `Fitnet.Contracts` (host) → `Contracts.Api` — `Fitnet.Contracts/Src/Fitnet.Contracts/Fitnet.Contracts.csproj:5`.
- `Contracts.Api` → `Contracts.Core`, `Contracts.Infrastructure`, `Contracts.Application` — `Fitnet.Contracts/Src/Fitnet.Contracts.Api/Fitnet.Contracts.Api.csproj:5-7`.
- `Contracts.Application` → `Contracts.Core`, `Contracts.IntegrationEvents` — `Fitnet.Contracts/Src/Fitnet.Contracts.Application/Fitnet.Contracts.Application.csproj:5-6`.
- `Contracts.Infrastructure` → `Contracts.Application`, `Contracts.Core` — `Fitnet.Contracts/Src/Fitnet.Contracts.Infrastructure/Fitnet.Contracts.Infrastructure.csproj:5-6`.

The Contracts edges form a strict **DAG** (Core is the leaf; Api composes Infrastructure+Application+Core), the classic Onion direction. No project-reference cycles.

## Cross-module coupling inside the monolith (NON-OBVIOUS)

Modules are *meant* to be decoupled, but two real couplings exist:

1. **Offers → Passes via a compile-time event-contract reference.** `Offers.Api` has a `ProjectReference` to `Passes.IntegrationEvents` so it can consume `PassExpiredEvent`. A change to that event's shape breaks Offers at compile time. — `Fitnet/Src/Offers/Fitnet.Offers.Api/Fitnet.Offers.Api.csproj:8`; consumer `Fitnet/Src/Offers/Fitnet.Offers.Api/Prepare/PassExpiredEventConsumer.cs:8`.
2. **Reports → Passes via the database** (no code reference at all). Reports issues raw Dapper SQL against the `"Passes"."Passes"` table directly. A schema change in Passes silently breaks Reports at query time — there is no compile-time link to catch it. — `Fitnet/Src/Reports/.../DataRetriever/NewPassesRegistrationPerMonthReportDataRetriever.cs:19`.

## Cross-application coupling (monolith ↔ microservice)

The monolith's **Passes** module consumes the microservice's **`ContractSignedEvent`** (delivered over RabbitMQ) via the `EvolutionaryArchitecture.Fitnet.Contracts.IntegrationEvents` NuGet package. — `Fitnet/Src/Passes/Fitnet.Passes.Api/RegisterPass/ContractSignedEventConsumer.cs:8`; package ref `Fitnet/Src/Passes/Fitnet.Passes.Api/Fitnet.Passes.Api.csproj:18`; version pin `Fitnet/Src/Directory.Packages.props:12`.

So the **end-to-end business flow crosses the deployment boundary asynchronously over the bus**, not via HTTP:

```
Contracts svc: Sign contract → publish ContractSignedEvent ──RabbitMQ──▶ Monolith/Passes: register Pass
Monolith/Passes: MarkAsExpired → publish PassExpiredEvent ──(in-proc bus)──▶ Monolith/Offers: prepare renewal Offer
```

## External package dependencies (centrally versioned)

Versions are pinned centrally via `Directory.Packages.props` (Central Package Management). — `Fitnet/Src/Directory.Packages.props:3` (`ManagePackageVersionsCentrally=true`).

| Package | Role | Evidence |
|---------|------|----------|
| MediatR 12.5.0 | in-process command/query + notification dispatch | `Fitnet/Src/Directory.Packages.props:18` |
| MassTransit.RabbitMQ 8.3.2 | message bus transport | `…props:17` |
| MassTransit.EntityFrameworkCore 8.3.2 | EF transactional outbox/inbox | `…props:16` |
| Microsoft.EntityFrameworkCore 10.0.1 + Npgsql.EntityFrameworkCore.PostgreSQL 10.0.0 | ORM + PG provider | `…props:21,29` |
| Dapper 2.1.66 | raw-SQL read access (Reports only) | `…props:8` |
| FluentValidation 12.0.0 | request validation | `…props:13` |
| ErrorOr (via Common) | result/error value type (no exceptions for business errors) | `Fitnet.Common.Core/BussinessRules/IBusinessRule.cs:1` |
| Scalar.AspNetCore 2.12.17 | OpenAPI UI at `/docs/v1` | `…props:31`; `Fitnet/Src/Fitnet/Program.cs:26` |
| Aspire.Hosting.PostgreSQL / RabbitMQ 13.1.0 | local orchestration (AppHost only) | `…props:6-7` |

## Build / runtime-target inconsistency (NON-OBVIOUS, [HIGH])

All csproj target **`net10.0`** (`Directory.Build.props:6` in all three trees), but the **Dockerfiles build/run on older SDK/runtime images**: the monolith Dockerfile uses `dotnet/sdk:9.0` + `aspnet:9.0` (`Fitnet/Src/Dockerfile:1,6`), and the Contracts Dockerfile uses `8.0` (`Fitnet.Contracts/Src/Dockerfile:1,6`). The Docker images would not build the `net10.0` projects as written — the container build path is stale relative to the code's target framework.

## Cascade-risk summary

- A change to `Fitnet.Common.Core` business-rule contracts ripples to **every** module and the microservice (shared package). Highest blast radius.
- A change to `Passes.IntegrationEvents.PassExpiredEvent` breaks **Offers** (compile-time) and any bus consumer.
- A change to the `Passes` DB schema breaks **Reports** (runtime, silent).
- A change to `Contracts.IntegrationEvents.ContractSignedEvent` (microservice's public contract) breaks the **monolith's Passes consumer** across the deployment boundary.
