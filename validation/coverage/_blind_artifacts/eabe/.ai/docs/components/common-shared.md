<!-- DeepInit extraction | Component: common-shared (Fitnet.Common.* NuGet libraries)
Run ID: blind-eabe-2026-06-13
Input files processed: Fitnet.Common/** (.cs,.csproj, Directory.Build.props)
Generated: 2026-06-13 -->

# Component: Fitnet.Common (shared NuGet libraries, v4.2.0)

## 1. Overview
Five libraries published as `EvolutionaryArchitecture.Fitnet.Common.*` (version `4.2.0`) and consumed by BOTH the monolith and the Contracts microservice as PackageReferences. They define the cross-cutting contracts both apps build on. — version `Fitnet.Common/Directory.Build.props:15`. Complexity: **Moderate**. [HIGH]

## 2. Common.Core (domain primitives + business-rules engine)
- `Entity` base — tracks domain events; `RecordEvent(IDomainEvent)` accumulates into `Events`. — `Fitnet.Common.Core/Entity.cs:7-27`.
- `ValueObject` base — value equality via `GetEqualityComponents`. — `Fitnet.Common.Core/ValueObject.cs:4-23`.
- `IDomainEvent` (`Id`, `OccuredAt`). — `Fitnet.Common.Core/IDomainEvent.cs:6-17`.
- **Business-rules engine** (note the misspelled namespace `BussinessRules`): `IBusinessRule { bool IsMet; Error Error; }`; `BusinessRuleValidator.Validate(params IBusinessRule[])` returns `ErrorOr<Success>`, collecting the `Error` of every unmet rule. — `Fitnet.Common.Core/BussinessRules/IBusinessRule.cs:3-8`, `BusinessRuleValidator.cs:5-14`. `BusinessRuleError` is custom error **type `100`**. — `BussinessRules/BusinessErrors.cs:5`.

## 3. Common.Api (error handling -> HTTP)
- `ExceptionMiddleware` — `ResourceNotFoundException` -> 404, everything else -> 500. — `Fitnet.Common.Api/ErrorHandling/ExceptionMiddleware.cs:32-37`. Wired via `UseErrorHandling`. — `ErrorHandling/ErrorHandlingExtensions.cs:9`.
- `ProblemResults.ToProblem(errors)` — the canonical `ErrorOr` -> HTTP map: BusinessRuleError(100)->409, Conflict->409, Validation->400, NotFound->404, Failure/Unexpected->500, Unauthorized->401, Forbidden->403. — `Fitnet.Common.Api/ErrorHandling/Problems/ProblemResults.cs:12-23`.
- `RequestValidationApiFilter<T>` + `ValidateRequest<T>` — FluentValidation endpoint filter -> 400 on failure. — `Validations/RequestValidationApiFilter.cs:8-30`.
- `ApiPaths.Root = "api"`. — `Fitnet.Common.Api/ApiPaths.cs:5`.

## 4. Common.Infrastructure (clock, events, mediator, modules)
- `AddClock` registers `TimeProvider.System` as singleton. — `Clock/ClockModule.cs:8`.
- `IIntegrationEvent: INotification` (`Id`, `OccurredDateTime`) + `IIntegrationEventHandler<TEvent>`. — `Events/IIntegrationEvent.cs:5-9`, `Events/IIntegrationEventHandler.cs:5-7`.
- `AddMediator(assembly)` -> `AddMediatR(RegisterServicesFromAssembly(assembly))`. — `Mediator/MediatorModule.cs:8-10`.
- `IsModuleEnabled(config, module)` reads `Modules:{module}:Enabled`. — `Modules/ModuleAvailabilityChecker.cs:9-12`.

## 5. Test toolboxes
- `Common.IntegrationTestsToolbox` — `FitnetWebApplicationFactory<T>`, `DatabaseContainer` (Testcontainers PostgreSQL), `FakeTimeProvider`, MassTransit test-harness helpers + event assertions. — `TestEngine/FitnetWebApplicationFactory.cs:4-15`, `TestEngine/Database/DatabaseContainer.cs:6-28`, `TestEngine/Time/FakeTimeProvider.cs:6-14`.
- `Common.UnitTesting` — `ErrorOr<Success>` fluent assertions (`BeSuccessful`, `ContainError`). — `Assertions/ErrorOr/ErrorOrSuccessAssertions.cs:9-27`.

## 6. Non-obvious / load-bearing
- **The business-rule pattern is the system's spine.** Domain invariants in both apps are `IBusinessRule`s composed by `BusinessRuleValidator`; every business-rule failure becomes a value (ErrorOr type 100) and surfaces as **HTTP 409 Conflict** via `ProblemResults`. — `ProblemResults.cs:14`.
- **Two error pipelines coexist:** legacy `ExceptionMiddleware` (exceptions, e.g. `ResourceNotFoundException`/`SignatureNotValidException` -> 404/500) AND the `ErrorOr`/`ProblemResults` value path (per-endpoint). A new endpoint must pick the right one. [MEDIUM] — `ExceptionMiddleware.cs:32-37` vs `ProblemResults.cs:12-23`.
- Namespace is misspelled `BussinessRules` (double-s) — a real gotcha for `using` statements. [HIGH] — `Fitnet.Common.Core/BussinessRules/`.
- These libs are pulled from a GitHub NuGet feed at build, not built from this tree. — `Fitnet/Src/Dockerfile:11`.
