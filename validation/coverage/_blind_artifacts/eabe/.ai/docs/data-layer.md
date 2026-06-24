<!-- DeepInit horizontal | Component: system-wide
Run ID: blind-eabe-2026-06-13
Input files processed: *Persistence.cs, *EntityConfiguration.cs, Migrations/*.cs, DatabaseModule.cs, DatabaseOptions.cs, appsettings*.json, AppHost/Program.cs, DataRetriever, OutboxExtensions.cs
Generated: 2026-06-13 -->

# Data Layer & Persistence

## Topology

PostgreSQL, accessed two ways: **EF Core** (Offers, Passes, Contracts) and **Dapper raw SQL** (Reports). Each bounded context owns a **named PostgreSQL schema**; the monolith's three modules share **one database** (separate schemas), and the microservice has its **own database**.

| App / module | Schema | DbContext | Access | Tables |
|--------------|--------|-----------|--------|--------|
| Monolith / Passes | `Passes` | `PassesPersistence` | EF Core | `Passes`, + MassTransit `InboxState`/`OutboxMessage`/`OutboxState` |
| Monolith / Offers | `Offers` | `OffersPersistence` | EF Core | `Offers` |
| Monolith / Reports | (none) | — | Dapper | reads `"Passes"."Passes"` |
| Microservice / Contracts | `Contracts` | `ContractsPersistence` | EF Core | `Contracts`, `BindingContracts`, `Annexes` |

Evidence: `Fitnet/Src/Passes/Fitnet.Passes.DataAccess/Database/PassesPersistence.cs:6-20`; `Fitnet/Src/Offers/Fitnet.Offers.DataAccess/Database/OffersPersistence.cs:5,13`; `Fitnet.Contracts/Src/Fitnet.Contracts.Infrastructure/Database/ContractsPersistence.cs:9-12`.

## Databases (Aspire AppHost)

- Monolith DB: `fitnetsdb` (db name `fitnet`), injected as `Database__ConnectionString`; RabbitMQ as `EventBus__ConnectionString`. — `Fitnet/Src/AppHost/Program.cs:9,16-17`.
- Microservice DB: `fitnetcontractsdb` (db name `fitnet`), injected as `Database__ConnectionString`; RabbitMQ as **`EventBus__Uri`**. — `Fitnet.Contracts/Src/AppHost/Program.cs:9,16-17`.
- Both AppHosts spin up Postgres `14.3` + RabbitMQ. — `Fitnet/Src/AppHost/Program.cs:6,11`.

## Connection-string config keys (per module — NOT one global string)

Each module reads its OWN nested config section, so connection strings are configured per module, not once:
- `Passes:Database:ConnectionString` — `Fitnet/Src/Fitnet/appsettings.json:20-23`.
- `Offers:Database:ConnectionString` — `…appsettings.json:30-33`.
- `Reports:Database:ConnectionString` — `…appsettings.json:25-28`.
- Microservice: `Database:ConnectionString` — `Fitnet.Contracts/Src/Fitnet.Contracts/appsettings.json:9-11`.

(In committed `appsettings.json` these are empty strings; real values come from the AppHost/env at run time.)

## Automatic migrations at startup (NON-OBVIOUS, [HIGH])

Every EF module calls `context.Database.Migrate` during host startup via an `AutomaticMigrationsExtensions.UseAutomaticMigrations` step — there is **no separate deploy-time migration step**; schema is created/upgraded on boot. — e.g. `Fitnet/Src/Passes/Fitnet.Passes.DataAccess/Database/AutomaticMigrationsExtensions.cs:13`; `Fitnet.Contracts/Src/Fitnet.Contracts.Infrastructure/Database/AutomaticMigrationsExtensions.cs:13`.

## Entity / value-object mapping

### Contracts (richest model)
- `Contract` — PK `Id` is a value object `ContractId(Guid)` with an EF value converter; `Signature` is an **EF owned type** stored as `Signature_Date` / `Signature_Value` (varchar(100)) on the `Contracts` table. — `Fitnet.Contracts/Src/Fitnet.Contracts.Infrastructure/Database/Configurations/ContractEntityConfiguration.cs:14-25`.
- `BindingContract` — separate table; `ContractId` foreign reference, `Duration` (interval), `BindingFrom`, `ExpiringAt`, nullable `TerminatedAt`. — `…/Configurations/BindingContractEntityConfiguration.cs:11-29`.
- `Annex` — **owned collection** of `BindingContract`, own table `Annexes`, composite key `(BindingContractId, Id)`, cascade-delete FK to `BindingContracts`. — `…/Configurations/BindingContractExtensions.cs:9-25`.

### Passes
- `Pass` — table `Passes` in schema `Passes`: `Id`, `CustomerId`, `From`, `To`; all required. — `Fitnet/Src/Passes/Fitnet.Passes.DataAccess/Database/PassEntityConfiguration.cs:8-14`. `To` is the only mutable column (set on expiry). — `Fitnet/Src/Passes/Fitnet.Passes.DataAccess/Pass.cs:21`.

### Offers
- `Offer` — table `Offers` in schema `Offers`: `Id`, `CustomerId`, `PreparedAt`, `Discount` (numeric), `OfferedFromDate`, `OfferedFromTo`; all required; immutable (init-only). — `Fitnet/Src/Offers/Fitnet.Offers.DataAccess/Database/OfferEntityConfiguration.cs:10-16`.

## Migration history

- **Passes**: 2 migrations — `CreatePassesTable` (20230503180338), `AddOutbox` (20231107192159, adds Inbox/Outbox tables). — `Fitnet/Src/Passes/Fitnet.Passes.DataAccess/Database/Migrations/`.
- **Offers**: 1 migration — `CreateOffersTable` (20230503180337). — `Fitnet/Src/Offers/Fitnet.Offers.DataAccess/Database/Migrations/`.
- **Contracts**: 10 migrations (May-2023 → Oct-2024), tracing the model's evolution: table create → add SignedAt → add PreparedAt → make SignedAt nullable → add CustomerId → add Duration/ExpiringAt → add BindingContracts table → add Annexes → make TerminatedAt nullable → replace SignedAt with owned `Signature` (Signature_Date/Signature_Value). — `Fitnet.Contracts/Src/Fitnet.Contracts.Infrastructure/Database/Migrations/` (10 dated `*.cs` migration classes).

## Messaging persistence — the outbox ASYMMETRY (NON-OBVIOUS, [HIGH])

- The **monolith's Passes** module wires a **MassTransit EF transactional outbox** over `PassesPersistence` (`UsePostgres`, `UseBusOutbox`, 30-second duplicate-detection window). Integration events are staged in the `OutboxMessage` table in the same transaction as the data write, then dispatched. — `Fitnet/Src/Passes/Fitnet.Passes.Api/Common/EventBus/Outbox/OutboxExtensions.cs:8-12`; outbox tables from `…/Migrations/20231107192159_AddOutbox.cs`.
- The **Contracts microservice does NOT use an outbox.** `SignContractCommandHandler` commits the DB transaction and THEN calls `publishEndpoint.Publish(ContractSignedEvent)` as a separate step — if the process dies after commit but before publish, the event is lost (no transactional guarantee). There are **no Inbox/Outbox migrations** in the Contracts schema. — `Fitnet.Contracts/Src/Fitnet.Contracts.Application/SignContract/SignContractCommandHandler.cs:20-25`; `Fitnet.Contracts/Src/Fitnet.Contracts.Infrastructure/EventBus/EventBusModule.cs` (no `AddEntityFrameworkOutbox`).

## Reports' cross-schema raw-SQL read (NON-OBVIOUS, [HIGH])

Reports does not own data; its single report runs Dapper SQL directly against another module's table, `FROM "Passes"."Passes"`, grouping pass registrations per month of `"From"` for the current UTC year. The year is interpolated into the SQL string from `TimeProvider.GetUtcNow.Year` (safe — server-derived int, not user input). — `Fitnet/Src/Reports/Fitnet.Reports/GenerateNewPassesRegistrationsPerMonthReport/DataRetriever/NewPassesRegistrationPerMonthReportDataRetriever.cs:15-22`. Its `DatabaseConnectionFactory` is a singleton that creates/reuses one `NpgsqlConnection`. — `Fitnet/Src/Reports/Fitnet.Reports/DataAccess/DatabaseConnectionFactory.cs:7-32`.
