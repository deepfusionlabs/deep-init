<!-- DeepInit detection | Component: system-wide
Run ID: blind-eabe-2026-06-13
Generated: 2026-06-13 -->

# Discovery

## 1. Project overview
"Fitnet" (EvolutionaryArchitecture) — a gym/fitness membership system, demonstrated as a **modular monolith + an extracted microservice + shared NuGet libraries**. ~238.cs files (164 production, excl. tests/obj/bin). No architecture doc, ADR, wiki, or README found in the input tree (`Docs/` holds only `.http` request samples). doc_in_inputs = false.

## 2. Tech stack
.NET 10 / C# (csproj `TargetFramework net10.0`); ASP.NET Core; EF Core 10 + Npgsql/PostgreSQL; Dapper (Reports); MediatR (in-proc); MassTransit + RabbitMQ (bus, EF outbox in Passes); FluentValidation; ErrorOr; Scalar OpenAPI;.NET Aspire (AppHost orchestration); xUnit/Testcontainers/Shouldly/NSubstitute (tests). Central Package Management via `Directory.Packages.props`.

## 3. Architecture style (confidence HIGH)
- **Fitnet** = modular monolith — one host composing feature modules (Offers/Passes/Reports), each its own PostgreSQL schema, communicating via an in-process + RabbitMQ event bus. Method: csproj graph + `Program.cs` module registration.
- **Fitnet.Contracts** = Clean/Onion microservice (Core/Application/Infrastructure/Api). Method: project-layer naming + ProjectReference DAG.
- **Fitnet.Common** = shared kernel published as NuGet packages (v4.2.0).

## 4. Component registry
| Component | Path | Type | Access |
|-----------|------|------|--------|
| contracts-service | Fitnet.Contracts/Src | microservice (4 layers) | EF Core + RabbitMQ |
| passes | Fitnet/Src/Passes | monolith module | EF Core + RabbitMQ (outbox host) |
| offers | Fitnet/Src/Offers | monolith module (event-only) | EF Core + RabbitMQ |
| reports | Fitnet/Src/Reports | monolith module | Dapper raw SQL |
| monolith-host | Fitnet/Src/Fitnet + AppHosts | hosts/orchestration | Aspire |
| common-shared | Fitnet.Common | shared NuGet libs (5) | n/a |

## 5. Git intelligence
Not analyzed (no git history probe performed in this blind run).

## 6. Database connectivity
PostgreSQL. Monolith: one DB (`fitnetsdb`), schemas Passes/Offers/(Reports reads Passes). Microservice: own DB (`fitnetcontractsdb`), schema Contracts. Connection strings per-module config; auto-migrate on startup. No live DB connection made (read-only static analysis; R7).

## 7. Legacy health flags
- Dockerfiles target.NET 8/9 images while code targets net10.0 (stale containers).
- Contracts EventBus config-section name mismatch (`EventBus` in code vs `ExternalEventBus` in appsettings).
- Contracts has no transactional outbox (lossy publish).
- Misspelled namespace `BussinessRules`.

## 8. Structural analysis status
Graphify/ctags not used; dependency graph built from the csproj ProjectReference/PackageReference manifests + `using`/registration reads (R6 manifest layer).

## 9. Cost estimate
N/A — blind validation run.
