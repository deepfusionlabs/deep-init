<!-- DeepInit extraction | Component: passes (Fitnet monolith module)
Run ID: blind-eabe-2026-06-13
Input files processed: Fitnet/Src/Passes/** (.cs,.csproj)
Generated: 2026-06-13 -->

# Component: Passes (monolith module)

## 1. Overview
Manages gym **membership passes**: provisions a Pass when a Contract is signed (cross-app event), lists passes, and marks a pass expired (publishing an event). Vertical-slice feature folders; EF Core + PostgreSQL (schema `Passes`); MassTransit + RabbitMQ with EF outbox. Complexity: **Moderate**. [HIGH]
- Projects: `Passes.Api` (endpoints/consumers/eventbus), `Passes.DataAccess` (EF + `Pass` aggregate), `Passes.IntegrationEvents` (`PassExpiredEvent`).

## 2. Entry points
- Module registration: `AddPasses(configuration, module)` (DI; gated by `IsModuleEnabled`) and `RegisterPasses(module)` (pipeline/endpoints). — `Fitnet/Src/Passes/Fitnet.Passes.Api/PassesModule.cs:14-38`. Called from host `Program.cs:16,37`.
- HTTP: `GET /api/passes` (`PassesApiPaths.GetAll`) — `Fitnet.Passes.Api/GetAllPasses/GetAllPassesEndpoint.cs:11-26`; `PATCH /api/passes/{id}` mark-as-expired (`PassesApiPaths.MarkPassAsExpired`) — `Fitnet.Passes.Api/MarkPassAsExpired/MarkPassAsExpiredEndpoint.cs:12-40`. Route constants `Fitnet.Passes.Api/PassesApiPaths.cs:7-8`.
- Event consumer: `ContractSignedEventConsumer: IConsumer<ContractSignedEvent>`. — `Fitnet.Passes.Api/RegisterPass/ContractSignedEventConsumer.cs:8-21`.

## 3. Domain model
`Pass` — `Id`, `CustomerId`, `From`, `To` (init-only except `To`). Factory `Register(customerId, from, to)`; `MarkAsExpired(now)` sets `To = now`. No creation-time invariant on `From < To`. — `Fitnet/Src/Passes/Fitnet.Passes.DataAccess/Pass.cs:18-21`.

## 4. Persistence
`PassesPersistence` DbContext, schema `Passes`, table `Passes`. 2 migrations: `CreatePassesTable`, `AddOutbox` (Inbox/Outbox tables). Auto-migrate on startup. — `Fitnet.Passes.DataAccess/Database/PassesPersistence.cs:6-20`, `PassEntityConfiguration.cs:8-14`, `Migrations/`.

## 5. Events
- **Consumes** `ContractSignedEvent` (from the Contracts microservice, over RabbitMQ; via the `…Contracts.IntegrationEvents` package). On receipt: `Pass.Register(ContractCustomerId, SignedAt, ExpireAt)`, persist, then publish `PassRegisteredEvent`. — `Fitnet.Passes.Api/RegisterPass/ContractSignedEventConsumer.cs:8-21`.
- **Publishes** `PassExpiredEvent(Id, PassId, CustomerId, OccurredDateTime)` on mark-as-expired — consumed in-process by Offers. — `Fitnet/Src/Passes/Fitnet.Passes.IntegrationEvents/PassExpiredEvent.cs:5-10`; published `MarkPassAsExpiredEndpoint.cs:30-31`.
- Consumer retry/redelivery policy: 3 immediate retries (1s) + scheduled redeliveries. — `Fitnet.Passes.Api/RegisterPass/ContractSignedEventConsumerDefinition.cs:11-20`.

## 6. Event bus (owns the monolith's MassTransit wiring)
`AddEventBus` configures MassTransit + RabbitMQ + the **EF transactional outbox** (`AddEntityFrameworkOutbox<PassesPersistence>`, `UsePostgres`, `UseBusOutbox`, 30s duplicate-detection). It also `AddConsumers(executing assembly)` and `SetSnakeCaseEndpointNameFormatter`. — `Fitnet.Passes.Api/Common/EventBus/EventBusModule.cs:14-52`, `Common/EventBus/Outbox/OutboxExtensions.cs:8-12`. Bus connects only when `EventBus:Uri` is non-empty (else MassTransit registers but no transport host is set). — `EventBusModule.cs:29-45`.

## 7. Dependencies
PackageRefs: `Common.Api`, `Common.Core`, `Contracts.IntegrationEvents`, `MassTransit.*`. ProjectRefs: `Passes.DataAccess`, `Passes.IntegrationEvents`. — `Fitnet.Passes.Api/Fitnet.Passes.Api.csproj:4-23`.

## 8. Non-obvious / load-bearing
- **Passes is the monolith's MassTransit host.** Its `AddEventBus` registers the bus + scans the executing assembly for consumers. Offers does NOT call `AddEventBus`; it relies on Passes being registered first in `Program.cs` (16 before 17) so `IPublishEndpoint` resolves. Disable/reorder Passes and Offers' consumer breaks. [HIGH] — `Program.cs:16-17`; `EventBusModule.cs:20`.
- `GetAllPasses` projects only `Id`+`CustomerId` (not `From`/`To`); read-only `AsNoTracking`. — `GetAllPassesEndpoint.cs:14-20`.
- `MarkAsExpired` has no guard against re-expiring an already-expired pass; it just resets `To` to now. — `Pass.cs:21`.
