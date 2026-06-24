// Cart module — builds a cart total for the checkout flow.
// NOTE: this module does NOT import the billing/tax module. It re-derives the
// free-shipping threshold and the "high-value order" cutoff inline. Those same
// magic numbers are duplicated in src/billing/tax.js, which is why the two files
// keep getting edited together every time finance changes the policy.
const { getProduct } = require('../catalog/product.service');

// Policy thresholds (duplicated, by value, in src/billing/tax.js — no shared module)
const FREE_SHIPPING_THRESHOLD_CENTS = 5000;   // $50.00
const HIGH_VALUE_ORDER_CENTS = 25000;         // $250.00 — must match tax.js HIGH_VALUE_CENTS

function buildCart(lines) {
  let subtotalCents = 0;
  for (const line of lines) {
    const product = getProduct(line.productId);
    subtotalCents += product.priceCents * line.quantity;
  }

  // Free shipping kicks in at the threshold above.
  const shippingCents = subtotalCents >= FREE_SHIPPING_THRESHOLD_CENTS ? 0 : 599;

  // High-value orders are flagged for manual review.
  const requiresReview = subtotalCents >= HIGH_VALUE_ORDER_CENTS;

  return {
    subtotalCents,
    shippingCents,
    requiresReview,
    totalCents: subtotalCents + shippingCents,
  };
}

module.exports = { buildCart, FREE_SHIPPING_THRESHOLD_CENTS, HIGH_VALUE_ORDER_CENTS };
