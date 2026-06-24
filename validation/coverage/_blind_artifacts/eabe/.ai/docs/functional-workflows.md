<!-- DeepInit horizontal | Component: system-wide
Run ID: blind-eabe-2026-06-13
Input files processed: handlers, consumers, endpoints across both apps
Generated: 2026-06-13 -->

# Functional Workflows (end-to-end)

## WF-001 — Prepare & sign a membership contract (Contracts svc)
1. `POST /api/contracts` -> `PrepareContractCommand` -> `Contract.Prepare` (age>=18, height<=210, previous-signed rules) -> persist. — `Fitnet.Contracts.Api/.../ContractsApiPaths.cs:13`; `Application/PrepareContract/PrepareContractCommandHandler.cs`.
2. `PATCH /api/contracts/{id}` -> `SignContractCommand` -> `Contract.Sign` (not-already-signed, within-30-days; builds `Signature` VO) -> create `BindingContract`, persist -> **publish `ContractSignedEvent` to RabbitMQ**. — `Application/SignContract/SignContractCommandHandler.cs:14-28`.

## WF-002 — Register a pass on contract signing (cross-app, async)
`ContractSignedEvent` (RabbitMQ) -> monolith `ContractSignedEventConsumer` -> `Pass.Register(ContractCustomerId, SignedAt, ExpireAt)` -> persist -> publish `PassRegisteredEvent`. — `Fitnet/Src/Passes/Fitnet.Passes.Api/RegisterPass/ContractSignedEventConsumer.cs:8-21`. Delivered through the Passes EF outbox; consumer retries 3x immediately + scheduled redeliveries. — `ContractSignedEventConsumerDefinition.cs:11-20`.

## WF-003 — Expire a pass and prepare a renewal offer (in-monolith, async)
1. `PATCH /api/passes/{id}` -> `Pass.MarkAsExpired(now)` -> persist -> publish `PassExpiredEvent`. — `MarkPassAsExpired/MarkPassAsExpiredEndpoint.cs:12-40`.
2. `PassExpiredEvent` -> `Offers.PassExpiredEventConsumer` -> `Offer.PrepareStandardPassExtension(CustomerId, now)` (10% / 1yr) -> persist -> publish `OfferPrepareEvent`. — `Fitnet/Src/Offers/Fitnet.Offers.Api/Prepare/PassExpiredEventConsumer.cs:8-23`.

## WF-004 — Attach annex / terminate binding contract (Contracts svc)
- `POST /api/binding-contracts/{id}/annexes` -> `AttachAnnex` (active + valid-from within period). — `ContractsApiPaths.cs:11`.
- `PATCH /api/binding-contracts/{id}/terminate` -> `Terminate` (only after 3-month lock-in). — `ContractsApiPaths.cs:12`.

## WF-005 — Monthly pass-registration report (Reports)
`GET {api}/reports/generate` -> Dapper SQL over `"Passes"."Passes"` grouped by month for the current year -> `NewPassesRegistrationsPerMonthResponse`. — `Reports/.../NewPassesRegistrationPerMonthReportDataRetriever.cs:15-22`.

## The big picture
```
[Contracts svc] Sign --ContractSignedEvent(RabbitMQ)--> [Monolith/Passes] Register Pass
[Monolith/Passes] Expire --PassExpiredEvent(in-proc bus)--> [Monolith/Offers] Prepare Offer
[Monolith/Reports] reads Passes table directly (SQL) for analytics
```
