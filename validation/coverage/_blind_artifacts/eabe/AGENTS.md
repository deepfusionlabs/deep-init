<!-- DEEPINIT:START (managed — regenerated on each run; edit OUTSIDE these markers) -->
# Fitnet — Agent Context

Gym/fitness **membership** system, shown as a **modular monolith + an extracted microservice + a shared NuGet kernel**, on.NET 10 / C#. Two apps integrate over RabbitMQ, not HTTP. Components map to `.ai/docs/components/`.

## Architecture
- **Fitnet** (`Fitnet/Src`) — a **modular monolith**: one ASP.NET Core host composes feature modules (Offers/Passes/Reports), each owning a PostgreSQL schema in one shared DB, talking over an in-process + RabbitMQ bus. — `Fitnet/Src/Fitnet/Program.cs:16-18`.
- **Fitnet.Contracts** (`Fitnet.Contracts/Src`) — an **extracted Clean/Onion microservice** (Core/Application/Infrastructure/Api), own host + own DB. — `Fitnet.Contracts/Src/Fitnet.Contracts/Program.cs:13`.
- **Fitnet.Common** — five **shared libs published as NuGet packages** `EvolutionaryArchitecture.Fitnet.Common.*` v4.2.0, consumed by BOTH apps. — `Fitnet.Common/Directory.Build.props:15`.
- Stack: EF Core 10 + Npgsql/PostgreSQL, Dapper (Reports only), MediatR, MassTransit+RabbitMQ, FluentValidation, ErrorOr, Scalar OpenAPI,.NET Aspire (AppHost). Versions pinned centrally in `Directory.Packages.props`.

## Components (6)
- **contracts-service** — gym-contract lifecycle microservice (Prepare/Sign/Annex/Terminate); publishes `ContractSignedEvent`. → `.ai/docs/components/contracts-service.md`
- **passes** — provisions a Pass on contract-sign; owns the monolith's MassTransit + EF outbox. → `.ai/docs/components/passes.md`
- **offers** — event-only module: prepares a renewal Offer when a Pass expires (no HTTP). → `.ai/docs/components/offers.md`
- **reports** — Dapper read-side analytics; reads the Passes table directly via SQL. → `.ai/docs/components/reports.md`
- **monolith-host** — Fitnet host + the two Aspire AppHosts (Postgres+RabbitMQ). → `.ai/docs/components/monolith-host.md`
- **common-shared** — Entity/ValueObject, the BusinessRule engine, error->HTTP mapping, clock, mediator, module gating. → `.ai/docs/components/common-shared.md`

## Dependencies / edges
Two mechanisms — `ProjectReference` (in-app, compile-time) vs `PackageReference` (NuGet: all `Common.*` + the cross-app `Contracts.IntegrationEvents`). The Common source tree is NOT in either app's build graph. — `Fitnet/Src/Dockerfile:11`.
- monolith host → offers, passes, reports — `Fitnet/Src/Fitnet/Fitnet.csproj:16-18`
- offers → passes.IntegrationEvents (compile-time) + offers.DataAccess — `Fitnet/Src/Offers/Fitnet.Offers.Api/Fitnet.Offers.Api.csproj:8-9`
- passes → passes.DataAccess + passes.IntegrationEvents — `Fitnet/Src/Passes/Fitnet.Passes.Api/Fitnet.Passes.Api.csproj:4-5`
- reports → Passes DB table directly (SQL, no code ref) — `Fitnet/Src/Reports/.../NewPassesRegistrationPerMonthReportDataRetriever.cs:19`
- contracts host → contracts.Api → {core, infrastructure, application}; application → {core, integrationEvents}; infrastructure → {application, core} (Onion DAG) — `Fitnet.Contracts/Src/Fitnet.Contracts.Api/Fitnet.Contracts.Api.csproj:5-7`
- monolith/passes consumes the microservice's `ContractSignedEvent` over RabbitMQ (NuGet pkg) — `Fitnet/Src/Passes/Fitnet.Passes.Api/RegisterPass/ContractSignedEventConsumer.cs:8`; pkg `Fitnet/Src/Directory.Packages.props:12`
- all feature modules → `Common.*` (NuGet) — e.g. `Fitnet/Src/Passes/Fitnet.Passes.Api/Fitnet.Passes.Api.csproj:18-20`

## Data layer
- PostgreSQL. Monolith = 1 DB `fitnetsdb`, schemas `Passes`/`Offers` (Reports reads `Passes`). Microservice = own DB `fitnetcontractsdb`, schema `Contracts`. — `Fitnet/Src/AppHost/Program.cs:9`, `Fitnet.Contracts/Src/AppHost/Program.cs:9`.
- Tables: `Passes` (`Passes.Passes`); `Offers` (`Offers.Offers`); `Contracts`/`BindingContracts`/`Annexes` (schema `Contracts`); + MassTransit Inbox/Outbox tables in the Passes schema only. — `data-layer.md`.
- Per-module connection-string config (`<Module>:Database:ConnectionString`); EF migrations run **automatically at startup** (`Database.Migrate`), no separate deploy step. — `Fitnet/Src/Passes/Fitnet.Passes.DataAccess/Database/AutomaticMigrationsExtensions.cs:13`.

## Critical to know (non-obvious, load-bearing)
- The end-to-end business flow is an **async event chain across the deployment boundary**: Contracts.Sign → `ContractSignedEvent`(RabbitMQ) → Passes.Register; Passes.Expire → `PassExpiredEvent` → Offers.PrepareOffer. There is no synchronous call between the apps. — `.ai/docs/functional-workflows.md`.
- **Passes is the monolith's only MassTransit registrar** (`AddEventBus` + scans its own assembly). Offers does NOT register the bus and only works because Passes is added first in `Program.cs:16-17`; reordering/disabling Passes breaks Offers' consumer + `IPublishEndpoint`. — `Fitnet/Src/Passes/Fitnet.Passes.Api/Common/EventBus/EventBusModule.cs:14-20`.
- **Outbox asymmetry**: the monolith's Passes uses an EF transactional outbox (30s dedup window); the **Contracts microservice has NO outbox** — `SignContractCommandHandler` publishes AFTER commit, so the event is lost on a crash between the two. — `Fitnet.Contracts/Src/Fitnet.Contracts.Application/SignContract/SignContractCommandHandler.cs:20-25`.
- **Reports → Passes coupling is through the database, not code**: a raw Dapper `FROM "Passes"."Passes"` query. A Passes schema change silently breaks Reports at query time with nothing at compile time to catch it. — `Fitnet/Src/Reports/.../NewPassesRegistrationPerMonthReportDataRetriever.cs:19`.
- **Business rules are the system spine**: domain invariants are `IBusinessRule`s composed by `BusinessRuleValidator` (returns `ErrorOr`, type 100); every business-rule failure surfaces as **HTTP 409 Conflict** via `ProblemResults`. The namespace is misspelled **`BussinessRules`**. — `Fitnet.Common.Core/BussinessRules/BusinessRuleValidator.cs:5-14`, `Fitnet.Common.Api/ErrorHandling/Problems/ProblemResults.cs:14`.
- Contract invariants worth knowing: adult age >= 18, height <= 210 cm, sign within 30 days of prepare, 365-day duration, 3-month termination lock-in. — `.ai/docs/components/contracts-service.md` §3.
- **Config / container drift**: Contracts' `EventBusModule` binds section `"EventBus"` but its appsettings define `"ExternalEventBus"` (only the AppHost-injected `EventBus__Uri` lines up); and Dockerfiles build on.NET 8/9 images though the code targets `net10.0`. — `Fitnet.Contracts/Src/Fitnet.Contracts.Infrastructure/EventBus/EventBusModule.cs:10` vs `Fitnet.Contracts/Src/Fitnet.Contracts/appsettings.json:12`; `Fitnet/Src/Dockerfile:1`.

## Where to look
- Component detail → `.ai/docs/components/<name>.md`
- Dependencies & cascade risk → `.ai/docs/technical-dependencies.md`
- Data & persistence → `.ai/docs/data-layer.md`
- Domain language → `.ai/docs/domain-model.md`
- End-to-end workflows → `.ai/docs/functional-workflows.md`
<!-- DEEPINIT:END -->
