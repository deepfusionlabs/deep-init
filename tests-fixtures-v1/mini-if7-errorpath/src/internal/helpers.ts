// internal/helpers.ts — has empty catches, but NOTHING here crosses a component boundary.
// A linter's no-empty / except:pass rule would flag both; IF-7 deliberately does NOT
// (a local concern, not a cross-boundary swallow). This is the gate proving IF-7 != no-empty.

// private (not exported) — a plain local empty catch, pure linter territory.
function tryParseJSON(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch (e) {}
  return undefined;
}

// exported, but consumed ONLY within the internal component (see format.ts) — not
// cross-consumed, so its empty catch stays a local concern (must NOT fire).
export function formatLabel(s: string): string {
  try {
    return String(tryParseJSON(JSON.stringify(s)) ?? s).trim().toUpperCase();
  } catch (e) {}
  return s;
}
