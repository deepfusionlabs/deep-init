// payments/session.ts — FINALLY-GUARD trap. Exported AND cross-consumed, with an empty catch —
// but a non-empty `finally` performs the cleanup, so this is a deliberate try/finally idiom, not a
// bare swallow. The deterministic slice fires only on a BARE empty handler (no compensating
// finally); the ambiguous finally case is deferred to the semantic layer. Must NOT fire.
declare const db: { open(): Promise<{ close(): void }> };

export async function withSession(orderId: string): Promise<void> {
  let conn: { close(): void } | undefined;
  try {
    conn = await db.open();
    // ... do work with conn for orderId
  } catch (e) {
    // intentionally absorbed; cleanup is guaranteed by the finally below
  } finally {
    conn?.close();
  }
}
