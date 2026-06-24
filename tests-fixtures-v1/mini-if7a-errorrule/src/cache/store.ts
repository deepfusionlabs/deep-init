// Cache store. BR-cache:002: on a cache-read failure, MUST fail OPEN and serve
// stale/origin data (availability over freshness).
import { readCache, readOrigin } from "./backend";

// T3 — DOCUMENTED FAIL-OPEN (must NOT fire): the catch ignores the read error
// and serves origin — exactly the REQUIRED behaviour under BR-cache:002.
export async function get(key: string): Promise<string> {
  try {
    return await readCache(key);
  } catch (e) {
    // fail open per BR-cache:002 — serve origin/stale
    return await readOrigin(key);
  }
}
