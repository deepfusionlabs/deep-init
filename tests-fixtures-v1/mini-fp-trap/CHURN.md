# Simulated git-intel for IF-5 (this fixture is not a real git repo)

The IF-5 overlay consumes `detection.md` git-intel (churn 6mo, bus-factor,
change-coupling). Since fixtures are not real repos, the intended signal is stated
here so the issue-oracle can assert the IF-5 *suppression* behaviour.

| File | 6mo commits | Authors | Co-changes with | Nature |
|------|-------------|---------|-----------------|--------|
| `src/shared/constants.ts` | 41 (highest in repo) | 6 | almost every file | Peripheral, no logic — labels/enums/page-size |
| `src/orders/orders.service.ts` | 4 | 2 | `orders.routes.ts` | Core business logic (writes) |
| `src/payments/reconcile.ts` | 2 | 1 | `payments.webhook.ts` | Core (payment reconciliation) |
| `app/models/order_report.rb` | 3 | 1 | (none structural) | Supporting (reporting) |

Expected IF-5 behaviour on this fixture:
- `constants.ts` is the highest-churn file but must NOT be ranked up as a risk
  hotspot (it is Peripheral, holds no behaviour) — a churn-only sort would
  wrongly bury the Core files. There is no real Core issue in this fixture to
  bury, but the ranking must still not elevate `constants.ts`.
- `constants.ts` co-changes with almost everything, but it is a shared
  *vocabulary* file, not a shared *resource* — its co-change pairs must NOT be
  promoted to IF-5 hidden-coupling or IF-3a.
