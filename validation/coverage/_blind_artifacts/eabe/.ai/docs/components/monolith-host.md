<!-- DeepInit extraction | Component: monolith-host (Fitnet host + Aspire AppHosts)
Run ID: blind-eabe-2026-06-13
Input files processed: Fitnet/Src/Fitnet/Program.cs, Module.cs, AppHost/Program.cs (x2)
Generated: 2026-06-13 -->

# Component: Hosts & Orchestration

## 1. Monolith host (Fitnet/Src/Fitnet)
ASP.NET Core composition root. Registers controllers, OpenAPI, `AddClock`, then `AddPasses/AddOffers/AddReports(configuration, Module.X)`; builds; maps OpenAPI + Scalar at `/docs/v1` in Development; `UseHttpsRedirection`, `UseAuthorization`, `UseErrorHandling`, `MapControllers`; then `RegisterPasses/RegisterOffers/RegisterReports`. — `Fitnet/Src/Fitnet/Program.cs:9-41`.
- `Module` is a typed enum-like record (`Offers`/`Passes`/`Reports`) with an implicit string conversion, used as the module key for config gating. — `Fitnet/Src/Fitnet/Module.cs:3-10`.
- **Registration order is load-bearing**: Passes is added before Offers, and Passes owns the MassTransit registration that Offers' consumer depends on. [HIGH] — `Program.cs:16-17`.

## 2. Microservice host (Fitnet.Contracts/Src/Fitnet.Contracts)
Same shape; registers `TimeProvider.System` explicitly + `AddClock`, then `AddContractsApi(configuration)`; Scalar at `/docs/v1`; `UseErrorHandling`; `RegisterContractsApi`. — `Fitnet.Contracts/Src/Fitnet.Contracts/Program.cs:8-29`.

## 3. Aspire AppHosts (local orchestration)
- Monolith AppHost: Postgres 14.3 (+pgAdmin) DB `fitnetsdb`, RabbitMQ (+mgmt), wires `Database__ConnectionString` and `EventBus__ConnectionString` into the `fitnet-modular-monolith` project, `WaitFor` both. — `Fitnet/Src/AppHost/Program.cs:5-19`.
- Contracts AppHost: Postgres 14.3 DB `fitnetcontractsdb`, RabbitMQ, wires `Database__ConnectionString` and **`EventBus__Uri`** into `fitnet-contracts`. — `Fitnet.Contracts/Src/AppHost/Program.cs:5-19`.

## 4. Non-obvious / load-bearing
- The two apps each have their OWN AppHost, DB, and run independently; they integrate only over RabbitMQ (the `ContractSignedEvent` -> Passes flow). [HIGH]
- The monolith AppHost injects the bus as `EventBus__ConnectionString` but the monolith's `EventBusModule` binds `EventBus:{Uri,Username,Password}` — the AppHost connection-string form vs the per-field form is a config-shape mismatch to watch. [MEDIUM] — `Fitnet/Src/AppHost/Program.cs:17` vs `Fitnet/Src/Passes/Fitnet.Passes.Api/Common/EventBus/EventBusModule.cs:16,29-31`.
