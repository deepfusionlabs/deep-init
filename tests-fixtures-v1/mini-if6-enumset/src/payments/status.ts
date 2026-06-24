// payments/status.ts — the order lifecycle as the payments component sees it (includes 'refunded').
export type OrderStatus = 'open' | 'paid' | 'shipped' | 'refunded';
