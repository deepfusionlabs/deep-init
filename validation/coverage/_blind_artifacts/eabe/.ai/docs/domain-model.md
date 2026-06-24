<!-- DeepInit horizontal | Component: system-wide
Run ID: blind-eabe-2026-06-13
Input files processed: Contract.cs, BindingContract.cs, Annex.cs, Signature.cs, Pass.cs, Offer.cs + business rules
Generated: 2026-06-13 -->

# Domain Model & Ubiquitous Language

Domain: a **gym / fitness membership** system ("Fitnet"). Three bounded contexts span two deployables.

## Contracts (microservice) — the rich domain
- **Contract** — a membership agreement drafted for a customer. Lifecycle: Prepared -> Signed -> (expires after Duration). Standard Duration = 365 days. — `Fitnet.Contracts.Core/Contract.cs:12,43-66`.
- **BindingContract** — the active agreement created when a Contract is signed; can have Annexes attached and can be terminated after a 3-month lock-in. — `Fitnet.Contracts.Core/BindingContract.cs:40-70`.
- **Annex** — a plan modification attached to an active BindingContract. — `Fitnet.Contracts.Core/Annex.cs:6-27`.
- **Signature** (VO) — letters+spaces only. — `Fitnet.Contracts.Core/SignContract/Signatures/Signature.cs:20-25`.
- Key constants: adult age 18, max height 210 cm, sign-within 30 days, lock-in 3 months, duration 365 days (see contracts-service.md §3 for the rule->file map).

## Passes (monolith)
- **Pass** — a membership pass for a customer over `[From, To]`, provisioned when a Contract is signed; can be expired early. — `Fitnet/Src/Passes/Fitnet.Passes.DataAccess/Pass.cs:18-21`.

## Offers (monolith)
- **Offer** — a renewal incentive (standard 10% discount, 1-year validity) prepared when a Pass expires. — `Fitnet/Src/Offers/Fitnet.Offers.DataAccess/Offer.cs:22-34`.

## Identity & customer linkage
There is **no shared Customer aggregate**; `CustomerId` (Guid) is the linking identifier carried on every aggregate and across every event (ContractSigned -> Pass.Register uses `ContractCustomerId`; PassExpired -> Offer uses `CustomerId`). — `Fitnet/Src/Passes/Fitnet.Passes.Api/RegisterPass/ContractSignedEventConsumer.cs:8-21`.

## Cross-context language note
"Sign a contract" (Contracts) is the trigger that "registers a pass" (Passes); "a pass expiring" (Passes) is the trigger that "prepares an offer" (Offers). The business process is a chain of events, not a synchronous call graph.
