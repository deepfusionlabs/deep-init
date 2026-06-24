export interface OrderLine {
  sku: string;
  unitPriceCents: number;
  quantity: number;
}

// ADR-002: money is integer minor units (cents). Returns an integer.
//
// BR-pricing:001 — "a discount reduces what the customer pays."
// The IMPLEMENTATION has legitimately evolved since the rule was recorded:
// originally a single flat 10% discount, it now supports volume tiers plus an
// optional coupon. This is an evolution of HOW the discount is computed, not a
// contradiction of the recorded intent — every branch still REDUCES the
// payable total. (This must NOT be over-flagged as ADR/BR DRIFTED.)
export function computeOrderTotal(lines: OrderLine[], couponCode?: string): number {
  const subtotal = lines.reduce(
    (sum, l) => sum + l.unitPriceCents * l.quantity,
    0,
  );

  const discount = discountFor(subtotal, couponCode);
  const total = subtotal - discount;

  // The rule's intent ("reduce what the customer pays") is preserved: total is
  // never above subtotal and never negative.
  return Math.max(0, total);
}

function discountFor(subtotalCents: number, couponCode?: string): number {
  let rate = 0;
  // Volume tiers (added after the rule was first recorded).
  if (subtotalCents >= 50000) rate = 0.15;
  else if (subtotalCents >= 20000) rate = 0.1;
  else if (subtotalCents >= 10000) rate = 0.05;

  // Coupon stacks a small extra reduction (also added later).
  if (couponCode === 'WELCOME') rate += 0.05;

  return Math.round(subtotalCents * rate);
}
