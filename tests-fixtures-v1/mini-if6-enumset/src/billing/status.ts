// billing/status.ts — DIVERGED copy of OrderStatus: billing's version is missing 'refunded'.
// A 'refunded' order produced by payments is a value billing's type cannot represent — the defect
// IF-6(enum-set) flags: a value one component produces that another rejects.
export type OrderStatus = 'open' | 'paid' | 'shipped';
