<!-- DeepInit | Phase: decisions | Run ID: 2026-05-20T09-00 -->
# Architecture Decision Records

## ADR-001 — Notifications MUST be dispatched asynchronously via the queue

- **Status:** Accepted (2025-11-03)
- **Context:** Notification providers (email/SMS) are slow and flaky. Early on we
  sent them inline inside the order-confirmation request handler; a provider
  timeout would block the HTTP response for up to 30s and occasionally fail the
  whole order. We had two incidents (INC-204, INC-219) where a downstream SMS
  outage took down order placement.
- **Decision:** All notification dispatch MUST enqueue a job and return
  immediately. Notifications are processed asynchronously by the queue worker.
  Request handlers MUST NOT call any notification provider synchronously inline.
- **Consequence:** Order placement never blocks on a notification provider. The
  queue worker owns retries/backoff. `NotificationQueue.enqueue()` is the only
  sanctioned dispatch path.
- **Provenance:** src/notifications/queue.ts (the sanctioned async path).

## ADR-002 — Money is stored and computed in integer minor units (cents)

- **Status:** Accepted (2025-09-12)
- **Context:** Floating-point arithmetic on currency produced rounding errors in
  invoice totals.
- **Decision:** All monetary values are integers in minor units (cents). No
  `number` field representing dollars; conversion to a display string happens
  only at the presentation edge.
- **Consequence:** `computeOrderTotal` returns an integer count of cents.
- **Provenance:** src/orders/pricing.ts

---

# Business Rules of record

| ID | Rule | Recorded intent | Source |
|----|------|-----------------|--------|
| BR-pricing:001 | Order discounts are applied to the order total | "A discount reduces what the customer pays" — the rule is about *reducing the payable total*, not the specific tiers. | src/orders/pricing.ts |
| BR-orders:001 | An order confirmation is sent after a successful order | "The customer is notified when their order is placed." | src/orders/order.service.ts |

---

# Known Workarounds

| ID | Workaround | Original triggering condition | Source |
|----|------------|-------------------------------|--------|
| WA-001 | `loadConfig()` reads the config file twice and merges, to defend against a partial-write race in the bundled `@acme/atomic-writer@1.x` whose `writeFileSync` was not actually atomic. | We pinned `@acme/atomic-writer@1.2.0`, which had a non-atomic write bug. | src/config/loader.ts |
