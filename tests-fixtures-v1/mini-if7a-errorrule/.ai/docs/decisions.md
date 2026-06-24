<!-- DeepInit | Phase: decisions | Run ID: 2026-06-09T12-00 -->
# Architecture Decision Records

## ADR-007 — Order-confirmation notifications MUST be enqueued, never sent inline

- **Status:** Accepted (2025-10-01)
- **Context:** Email/SMS providers are slow and flaky; an inline send on the
  request path blocks order placement and caused two incidents.
- **Decision:** On the **success path**, order confirmation MUST enqueue a job
  via `NotificationQueue.enqueue()` and return immediately. Request handlers MUST
  NOT call a provider synchronously inline.
- **Consequence:** This is a *happy-path* dispatch rule — it governs the normal
  success flow, not error handling.
- **Provenance:** src/orders/order.service.ts

## ADR-014 — On payment failure the order MUST NOT be marked paid

- **Status:** Accepted (2025-11-12)
- **Context:** A declined/failed charge that still flipped the order to `paid`
  shipped goods that were never paid for (INC-330). The failure path is the
  dangerous one because it is exercised by almost no tests.
- **Decision:** If `chargeCard()` throws or returns a non-success, the order
  status MUST NOT be set to `paid`, and no fulfilment MUST be triggered, on the
  error path. **EXCEPTION:** on a *duplicate-charge idempotency replay*
  (`err.code === 'idempotency_replay'`), the prior charge already succeeded, so
  the order MAY be marked paid — this is the one sanctioned case.
- **Consequence:** A `catch` around the charge MUST NOT call `markPaid()` /
  `order.status = 'paid'` except in the idempotency-replay branch.
- **Provenance:** src/payments/charge.ts

## ADR-021 — A failed outbox write MUST abort the transaction (event not published)

- **Status:** Accepted (2026-01-20)
- **Context:** The transactional-outbox pattern requires the event row and the
  business write to commit atomically. If the outbox INSERT fails, treating the
  event as published loses it forever.
- **Decision:** If the outbox write fails on the error path, the event MUST NOT
  be considered published and the surrounding transaction MUST be aborted
  (rolled back) — never committed.
- **Consequence:** A `catch` around the outbox write MUST NOT call `tx.commit()`.
- **Provenance:** src/payments/outbox.ts

## ADR-002 — Money is stored and computed in integer minor units (cents)

- **Status:** Accepted (2025-09-12)
- **Context:** Floating-point currency math produced rounding errors.
- **Decision:** All monetary values are integers in minor units (cents). This is
  a *representation* rule; it says nothing about error/failure behaviour.
- **Provenance:** src/money/pricing.ts

## ADR-009 — [SUPERSEDED] On a gateway timeout the charge MUST NOT be retried

- **Status:** Superseded (2026-02-01) — the idempotency-key handling in ADR-014
  makes a single keyed retry safe.
- **Decision (NO LONGER IN FORCE):** A gateway timeout MUST NOT trigger a retry
  (it risked double-charging). This is **superseded**: a single keyed retry is
  now safe and sanctioned. Code that retries a timed-out charge with an
  idempotency key conforms to **current** policy and only "contradicts" this
  superseded record — never cite ADR-009 to flag it.
- **Provenance:** src/legacy/session.ts

---

# Business Rules of record

| ID | Rule | Recorded intent | Source |
|----|------|-----------------|--------|
| BR-cache:002 | On a cache-read failure, the cache layer MUST **fail open** and serve stale/origin data. | "Availability over freshness — a cache outage must never take down reads." This is a *documented fail-open* policy: ignoring the read error on the failure path is the REQUIRED behaviour. | src/cache/store.ts |
| BR-inv:001 | On a partial reservation failure, the already-reserved units MUST be released. | "Never leak a half-reservation." This mandates a *compensating action* on the error path (an omission-class rule). | src/inventory/reserve.ts |
