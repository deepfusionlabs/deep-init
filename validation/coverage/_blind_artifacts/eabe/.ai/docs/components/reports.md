<!-- DeepInit extraction | Component: reports (Fitnet monolith module)
Run ID: blind-eabe-2026-06-13
Input files processed: Fitnet/Src/Reports/** (.cs,.csproj)
Generated: 2026-06-13 -->

# Component: Reports (monolith module)

## 1. Overview
Read-side **analytics**: a single report counting new pass registrations per month for the current year. Uses **Dapper raw SQL** (not EF Core) and reads another module's table directly. Complexity: **Simple**. [HIGH]

## 2. Entry points
- Module registration: `AddReports(configuration, module)` / `RegisterReports(module)` (gated by `IsModuleEnabled`). — `Fitnet/Src/Reports/Fitnet.Reports/ReportsModule.cs:12-35`. Called from host `Program.cs:18,39`.
- HTTP: `GET {api}/reports/generate` (`ReportsApiPaths`). — `Fitnet.Reports/ReportsApiPaths.cs:8`; `GenerateNewPassesRegistrationsPerMonthReport/GenerateNewPassesPerMonthReportEndpoint.cs:11-24`.

## 3. Data access
- `IDatabaseConnectionFactory` / `DatabaseConnectionFactory` (singleton; one reused `NpgsqlConnection`). Config section `Reports:Database`. — `Fitnet.Reports/DataAccess/DatabaseConnectionFactory.cs:7-32`, `DataAccess/DatabaseAccessModule.cs:8-13`.
- `NewPassesRegistrationPerMonthReportDataRetriever` runs Dapper SQL `FROM "Passes"."Passes"`, grouping by month of `"From"` filtered to `EXTRACT(YEAR...) = <TimeProvider.GetUtcNow.Year>`. — `.../DataRetriever/NewPassesRegistrationPerMonthReportDataRetriever.cs:15-22`.

## 4. DTOs
`NewPassesRegistrationsPerMonthDto(MonthOrder, MonthName, RegisteredPasses)`; `NewPassesRegistrationsPerMonthResponse.Create(...)`. — `.../Dtos/NewPassesRegistrationsPerMonthDto.cs:3`, `.../Dtos/NewPassesRegistrationsPerMonthResponse.cs:3-5`.

## 5. Dependencies
PackageRefs `Common.Api`, `Common.Core`, `Common.Infrastructure`, `Dapper`, `Npgsql`, `MassTransit.RabbitMQ`. — `Fitnet.Reports/Fitnet.Reports.csproj:6-14`.

## 6. Non-obvious / load-bearing
- **Cross-module DB coupling.** Reports reads the Passes module's `"Passes"."Passes"` table directly via SQL — no API or event. A Passes schema change silently breaks the report at query time. [HIGH] — `NewPassesRegistrationPerMonthReportDataRetriever.cs:19`.
- The year filter is string-interpolated into the SQL, but the value is a server `int` from `TimeProvider` — not user-controlled, so no injection here. [MEDIUM] — `...DataRetriever.cs:20`.
- `MassTransit.RabbitMQ` is referenced but Reports has **no consumers/publishers** — currently unused. [MEDIUM] — `Fitnet.Reports.csproj:10`.
