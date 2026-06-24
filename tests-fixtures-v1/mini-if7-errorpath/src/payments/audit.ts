// payments/audit.ts — FUNCTION-SCOPE trap. This file EXPORTS a clean, cross-consumed function
// (recordAudit — no swallowed error on its path) AND ALSO contains a PRIVATE helper with a
// harmless empty catch (debugDump). Under FILE-granularity attribution this file would wrongly
// fire and mis-pin the swallow on recordAudit; the spec requires the empty catch to be bound to
// its ENCLOSING exported+cross-consumed function, so the detector must NOT fire here.
declare const sink: { write(s: string): void };

// private (not exported): a best-effort debug helper — its empty catch is local linter territory.
function debugDump(x: unknown): void {
  try {
    sink.write(JSON.stringify(x));
  } catch (e) {}
}

// exported AND cross-consumed by gateway, but its OWN body swallows nothing.
export function recordAudit(orderId: string, ref: string): void {
  debugDump({ orderId, ref });
  sink.write('audit:' + orderId + ':' + ref);
}
