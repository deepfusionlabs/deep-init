// Inventory reservation. BR-inv:001: on a partial reservation failure, the
// already-reserved units MUST be released (a compensating action).
import { reserveUnit } from "./store";

// T9 — OMISSION (DEFERRED sub-type; must NOT fire in the commission-first ship):
// the catch fails to perform the required release (BR-inv:001) but commits NO
// forbidden effect — omission-from-absence, gated behind its own measurement.
export async function reserve(skus: string[]): Promise<void> {
  const reserved: string[] = [];
  try {
    for (const sku of skus) {
      await reserveUnit(sku);
      reserved.push(sku);
    }
  } catch (e) {
    // omission: should releaseAll(reserved) per BR-inv:001, but does not
    console.error("reservation failed", e);
  }
}
