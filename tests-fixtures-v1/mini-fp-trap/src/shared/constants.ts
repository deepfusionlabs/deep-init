// Trivial, high-churn constants/config file.
//
// This file changes on nearly every release (someone bumps a label, adds a status
// string, tweaks a copy constant). Its git churn is the HIGHEST in the repo and it
// co-changes with many files. But it is Peripheral, has no behaviour/logic, and
// holds no business rule. IF-5 must NOT rank it up as a risk hotspot on churn
// alone (mirror filter.md's behaviour-change-first ranking), and a co-change with
// it must NOT be promoted to IF-3a/IF-5 hidden coupling — it is a shared *vocabulary*
// file, not a shared *resource*.

export const ORDER_STATUSES = ['pending', 'paid', 'cancelled', 'refunded'] as const;
export const EVENT_TYPES = ['payment.succeeded', 'payment.refunded', 'order.cancelled'] as const;

export const DEFAULT_PAGE_SIZE = 25;
export const MAX_PAGE_SIZE = 100;

export const LABELS = {
  orderCreated: 'Order created',
  orderCancelled: 'Order cancelled',
  paymentReceived: 'Payment received',
  paymentRefunded: 'Payment refunded',
};

export const SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP'];
