<!-- DeepInit extraction | Component: offers (Fitnet monolith module)
Run ID: blind-eabe-2026-06-13
Input files processed: Fitnet/Src/Offers/** (.cs,.csproj)
Generated: 2026-06-13 -->

# Component: Offers (monolith module)

## 1. Overview
Generates a **renewal offer** (standard discount) when a customer's pass expires. Purely event-driven — **no HTTP endpoints**. EF Core + PostgreSQL (schema `Offers`). Complexity: **Simple**. [HIGH]
- Projects: `Offers.Api` (consumer + module reg), `Offers.DataAccess` (EF + `Offer`).

## 2. Entry points
- Module registration: `AddOffers(configuration, module)` / `RegisterOffers(module)` (both gated by `IsModuleEnabled`). — `Fitnet/Src/Offers/Fitnet.Offers.Api/OffersModule.cs:13-35`. Called from host `Program.cs:17,38`.
- Event consumer (the only runtime entry): `PassExpiredEventConsumer: IConsumer<PassExpiredEvent>`. — `Fitnet.Offers.Api/Prepare/PassExpiredEventConsumer.cs:8-23`. No route mapping exists.

## 3. Domain model
`Offer` — immutable (init-only) `Id`, `CustomerId`, `PreparedAt`, `Discount`, `OfferedFromDate`, `OfferedFromTo`. Factory `PrepareStandardPassExtension(customerId, nowDate)`: **hardcoded 10% discount** (`const decimal standardDiscount = 0.1m`), valid `now → now.AddYears(1)`. — `Fitnet/Src/Offers/Fitnet.Offers.DataAccess/Offer.cs:22-34`.

## 4. Persistence
`OffersPersistence` DbContext, schema `Offers`, table `Offers`. 1 migration `CreateOffersTable`. Auto-migrate on startup. — `Fitnet.Offers.DataAccess/Database/OffersPersistence.cs:5-13`, `OfferEntityConfiguration.cs:10-16`.

## 5. Events
- **Consumes** `PassExpiredEvent` (from the Passes module, in-process bus; via a compile-time `ProjectReference` to `Passes.IntegrationEvents`). — `Fitnet.Offers.Api/Prepare/PassExpiredEventConsumer.cs:8`; ref `Fitnet.Offers.Api/Fitnet.Offers.Api.csproj:8`.
- On receipt: create Offer, persist, then publish `OfferPrepareEvent(Id, OfferId, CustomerId, OccurredDateTime)`. — `PassExpiredEventConsumer.cs:16-21`; `Prepare/OfferPrepareEvent.cs:5-9`.

## 6. Dependencies
PackageRef `Common.Core`; ProjectRefs `Passes.IntegrationEvents`, `Offers.DataAccess`. — `Fitnet.Offers.Api/Fitnet.Offers.Api.csproj:8-17`.

## 7. Non-obvious / load-bearing
- **Compile-time coupling to Passes** via the `Passes.IntegrationEvents` project reference (not a package). A change to `PassExpiredEvent` breaks Offers at build. [HIGH] — `Fitnet.Offers.Api.csproj:8`.
- **No own event-bus registration.** Offers' consumer + `IPublishEndpoint` only work because the Passes module registered MassTransit (and scanned its own assembly). This is implicit ordering coupling. [HIGH] — see passes.md §8.
- 10% discount and 1-year validity are hardcoded, not configurable. — `Offer.cs:24,31`.
- No transactional outbox in Offers; publish is a separate step after SaveChanges. — `PassExpiredEventConsumer.cs:18-21`.
