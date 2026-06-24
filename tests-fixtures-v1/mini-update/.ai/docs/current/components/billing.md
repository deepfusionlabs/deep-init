<!-- DeepInit Wave 2 | Phase: component | Component: billing | Run ID: 2026-05-01T10-00 -->
# Billing Component
## Business Rules
| ID | Rule | Source |
|----|------|--------|
| BR-billing:001 | Invoice amount must be positive | src/billing/invoice.ts:3 |
| BR-billing:002 | Payment cannot exceed invoice amount | src/billing/payment.ts:2 |
## Integration Points
| ID | Integration | Source |
|----|-------------|--------|
| IP-billing:001 | Stripe API | src/billing/payment.ts:3 |
