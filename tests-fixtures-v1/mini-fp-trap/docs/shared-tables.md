# Shared tables & their contracts

## ADR-014 — `order_events` is a contracted shared table

**Status:** Accepted (2025-11-02)

**Decision.** The `order_events` table is intentionally shared between two
components:

| Component | Access | Mechanism |
|-----------|--------|-----------|
| `src/orders` (orders service) | **WRITE** (sole writer) | application DB role `orders_rw` |
| `app/models/order_report.rb` (reporting) | **READ-ONLY** | DB role `reporting_ro`, SELECT-only grant |

**Interface / contract.** The event schema (`order_id`, `event_type`, `payload`,
`occurred_at`) is the published interface. The orders service guarantees:
- `event_type` is drawn from the documented enum (`payment.succeeded`,
  `payment.refunded`, `order.cancelled`);
- events are append-only and never deleted.

Because the coupling is **explicit, asymmetric (one writer / one read-only
reader), and contracted**, it is NOT silent cross-component coupling. Changes to
the event schema are coordinated through this ADR. Do not flag as IF-3a.

## ADR-007 — Money columns use `NUMERIC`/`decimal`

`NUMERIC` (Postgres) is mapped as `decimal` in the ORM. These are exact synonyms;
the precision/scale `(12,2)` is identical on both sides. A type-equivalence check
must treat `numeric(12,2)` and `decimal(12,2)` as the same type.
