// payments/rates.ts — cross-consumed by gateway, but its catch is a DELIBERATE fallback
// (logs + returns an explicit default). A non-empty error-as-value contract, not a silent
// swallow. Must NOT fire (the deterministic slice keys strictly on an empty/comment-only body).
declare const logger: { warn(msg: string, e: unknown): void };
declare const live: { rate(ccy: string): number };

export function getRateWithFallback(ccy: string): number {
  try {
    return live.rate(ccy);
  } catch (e) {
    logger.warn('rate lookup failed, using documented fallback', e);
    return 1.0; // explicit, intentional fallback — a deliberate contract
  }
}
