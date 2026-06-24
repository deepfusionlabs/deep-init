// Tax / billing module — computes tax and surcharges for an order.
// NOTE: this module does NOT import the checkout/cart module. It hard-codes the
// SAME high-value cutoff that cart.js uses, by value. When finance changes the
// "high-value" policy, BOTH files must be edited in lock-step — but nothing in
// the code expresses that dependency. This is hidden (temporal) coupling.

// Duplicated policy threshold — must stay in sync with cart.js HIGH_VALUE_ORDER_CENTS
const HIGH_VALUE_CENTS = 25000;               // $250.00
const STANDARD_TAX_RATE = 0.085;              // 8.5%
const HIGH_VALUE_SURCHARGE_RATE = 0.015;      // extra 1.5% compliance surcharge on high-value orders

function computeTax(subtotalCents) {
  let rate = STANDARD_TAX_RATE;

  // High-value orders carry an extra compliance surcharge.
  if (subtotalCents >= HIGH_VALUE_CENTS) {
    rate += HIGH_VALUE_SURCHARGE_RATE;
  }

  return Math.round(subtotalCents * rate);
}

module.exports = { computeTax, HIGH_VALUE_CENTS };
