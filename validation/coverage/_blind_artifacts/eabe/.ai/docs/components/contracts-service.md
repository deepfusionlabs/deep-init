<!-- DeepInit extraction | Component: contracts-service (Fitnet.Contracts microservice)
Run ID: blind-eabe-2026-06-13
Input files processed: Fitnet.Contracts/Src/** (.cs,.csproj, appsettings, Dockerfile)
Generated: 2026-06-13 -->

# Component: Fitnet.Contracts (extracted microservice)

## 1. Overview
Standalone gym-membership **Contract lifecycle** service, extracted from the Fitnet monolith. Clean/Onion architecture in four projects: **Core** (domain), **Application** (MediatR use-cases + ports), **Infrastructure** (EF Core + repositories + RabbitMQ), **Api** (HTTP endpoints + composition). Own PostgreSQL DB, own host. Complexity: **Complex**. [HIGH]
- Host/entry: `Fitnet.Contracts/Src/Fitnet.Contracts/Program.cs:6-29`.
- Composition root: `AddContractsApi(configuration)` → `AddInfrastructure(...)`. `Fitnet.Contracts/Src/Fitnet.Contracts.Infrastructure/ContractsModule.cs:16-18`.

## 2. Domain model (Core)
Lifecycle: **Prepare → Sign → (Annex*) → Terminate / Expire**.
- `Contract` aggregate — factory `Prepare(customerId, customerAge, customerHeight, preparedAt, isPreviousContractSigned?)` returns `ErrorOr<Contract>`. Standard duration = `TimeSpan.FromDays(365)`. — `Fitnet.Contracts/Src/Fitnet.Contracts.Core/Contract.cs:12,43-53`. `Sign(signature, now)` returns `ErrorOr<BindingContract>`, sets `ExpiringAt = now + Duration`. — `Contract.cs:55-66`.
- `BindingContract` aggregate — created on signing; `AttachAnnex(validFrom, now)` and `Terminate(terminatedAt)`. — `Fitnet.Contracts/Src/Fitnet.Contracts.Core/BindingContract.cs:40-70`.
- `Annex` entity (owned by BindingContract). — `Fitnet.Contracts/Src/Fitnet.Contracts.Core/Annex.cs:6-27`.
- Value objects: `Signature` (regex `^[A-Za-z\s]+$`, else `SignatureNotValidException`) — `Core/SignContract/Signatures/Signature.cs:20-25`; `ContractId`/`BindingContractId`/`AnnexId` record-struct wrappers — `BindingContract.cs:73-81`, `Annex.cs:29-32`.

## 3. Business rules (Core) — all return ErrorOr, mapped to HTTP 409
| Rule | Invariant | Source |
|------|-----------|--------|
| ContractCanBePreparedOnlyForAdultRule | age >= 18 | `Core/PrepareContract/BusinessRules/ContractCanBePreparedOnlyForAdultRule.cs:11` |
| CustomerMustBeSmallerThanMaximumHeightLimitRule | height <= 210 cm (gym-instrument limit) | `Core/PrepareContract/BusinessRules/CustomerMustBeSmallerThanMaximumHeightLimitRule.cs:7,13` |
| PreviousContractHasToBeSignedRule | a prior contract (if any) must be signed | `Core/PrepareContract/BusinessRules/PreviousContractHasToBeSignedRule.cs:11` |
| ContractMustNotBeAlreadySignedRule | sign once only | `Core/SignContract/BusinessRules/ContractMustNotBeAlreadySignedRule.cs:7` |
| ContractCanOnlyBeSignedWithin30DaysFromPreparationRule | sign within 30 days of prepare (date-only) | `Core/SignContract/BusinessRules/ContractCanOnlyBeSignedWithin30DaysFromPreparationRule.cs:18-21` |
| AnnexCanOnlyBeAttachedToActiveBindingContractRule | not terminated & not expired | `Core/AttachAnnexToBindingContract/BusinessRules/AnnexCanOnlyBeAttachedToActiveBindingContractRule.cs:21` |
| AnnexCanOnlyStartDuringBindingContractPeriodRule | annex validFrom <= expiry | `Core/AttachAnnexToBindingContract/BusinessRules/AnnexCanOnlyStartDuringBindingContractPeriodRule.cs:18` |
| TerminationIsPossibleOnlyAfterThreeMonthsHavePassedRule | 3-month lock-in before terminate | `Core/TerminateBindingContract/BusinessRules/TerminationIsPossibleOnlyAfterThreeMonthsHavePassedRule.cs:8,14` |

Rules are composed via `BusinessRuleValidator.Validate(rule1, rule2, …)` (from Common.Core); failures short-circuit to an `ErrorOr` error of type `100` (BusinessRuleError). — `Fitnet.Common.Core/BussinessRules/BusinessRuleValidator.cs:5-14`.

## 4. Application layer (MediatR use-cases)
Commands: `PrepareContractCommand`, `SignContractCommand`, `AttachAnnexToBindingContractCommand`, `TerminateBindingContractCommand`; each with a `…CommandHandler`. Ports: `IContractsRepository`, `IBindingContractsRepository` (both expose `GetByIdAsync`/`AddAsync`/`CommitAsync`). — `Fitnet.Contracts/Src/Fitnet.Contracts.Application/IContractsRepository.cs:5-11`, `IBindingContractsRepository.cs:5-10`.

## 5. Entry points (Api)
| Route | Verb | Constant | Source |
|-------|------|----------|--------|
| `/api/contracts` | POST | `ContractsApiPaths.Prepare` | `Fitnet.Contracts.Api/.../ContractsApiPaths.cs:13` |
| `/api/contracts/{id}` | PATCH | `Sign` | `…ContractsApiPaths.cs:14` |
| `/api/binding-contracts/{id}/annexes` | POST | `AttachAnnex` | `…ContractsApiPaths.cs:11` |
| `/api/binding-contracts/{id}/terminate` | PATCH | `Terminate` | `…ContractsApiPaths.cs:12` |

Endpoints validate requests with FluentValidation (`PrepareContractRequestValidator`, `SignContractRequestValidator` — Signature NotEmpty + MaxLength 100). — `Fitnet.Contracts.Api/PrepareContract/PrepareContractRequestValidator.cs:9-12`, `SignContract/SignContractRequestValidator.cs:11-16`. Errors map to HTTP via `ProblemResults` (BusinessRuleError→409, Validation→400, NotFound→404, Failure/Unexpected→500). — `Fitnet.Contracts.Api/.../ProblemResults.cs:14-22`.

## 6. Persistence (Infrastructure)
`ContractsPersistence` DbContext, schema `"Contracts"`, `DbSet<Contract>` + `DbSet<BindingContract>`. EF value-converters for the id value objects, owned `Signature`, owned `Annexes` collection (cascade delete). 10 migrations. PostgreSQL via `UseNpgsql`. — `Fitnet.Contracts.Infrastructure/Database/ContractsPersistence.cs:9-12`, `DatabaseModule.cs:12,20`. See data-layer.md for full mapping + migration list.

## 7. Integration events (PUBLIC CONTRACT)
`Fitnet.Contracts.IntegrationEvents.ContractSignedEvent(Id, ContractId, ContractCustomerId, SignedAt, ExpireAt, OccurredDateTime)` is the service's public bus contract; published in `SignContractCommandHandler` after commit. Consumed by the monolith's Passes module. — `Fitnet.Contracts.IntegrationEvents/ContractSignedEvent.cs:3-14`; published `Fitnet.Contracts.Application/SignContract/SignContractCommandHandler.cs:21-25`. The four **domain** events (ContractPrepared, BindingContractStarted, AnnexAttached, BindingContractTerminated) are internal-only — recorded on the aggregate, not published to the bus.

## 8. Non-obvious / load-bearing
- **No transactional outbox.** Publish happens after commit as a separate await — at-most-once, lossy on crash. — `SignContractCommandHandler.cs:20-25`. (Contrast: the monolith's Passes uses an EF outbox.)
- **EventBus config-key mismatch.** `EventBusModule` binds the `"EventBus"` config section (`Fitnet.Contracts.Infrastructure/EventBus/EventBusModule.cs:10`), but the service's own `appsettings.json` defines a section named **`"ExternalEventBus"`** (`Fitnet.Contracts/Src/Fitnet.Contracts/appsettings.json:12`); the AppHost injects `EventBus__Uri` (`Fitnet.Contracts/Src/AppHost/Program.cs:17`). So local config and code disagree on the section name — only the AppHost-injected `EventBus__Uri` path lines up. [HIGH]
- **Repositories commit eagerly** (`AddAsync` + `CommitAsync` / direct SaveChanges) — no unit-of-work spanning the request. — `…/Repositories/ContractsRepository.cs:24-31`.
- Schema name `"Contracts"` is hardcoded, not configurable. — `ContractsPersistence.cs:9`.
- Dockerfile builds on **.NET 8** images while csproj targets `net10.0`. — `Fitnet.Contracts/Src/Dockerfile:1,6` vs `Fitnet.Contracts/Src/Directory.Build.props:6`.
