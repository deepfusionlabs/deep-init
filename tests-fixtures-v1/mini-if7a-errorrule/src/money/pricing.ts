// Pricing. ADR-002: money is stored/computed in integer minor units (cents) —
// a representation rule, NOT an error-handling rule (no failure clause).
import { fetchRate } from "./rates";

// T5 — RULE-NOT-ABOUT-ERRORS (must NOT fire): ADR-002 has no failure clause; the
// catch's default-rate fallback is unrelated to any documented error invariant.
export async function totalCents(subtotalCents: number, currency: string): Promise<number> {
  let rate = 100;
  try {
    rate = await fetchRate(currency);
  } catch (e) {
    rate = 100; // default rate; ADR-002 says nothing about error behaviour
  }
  return Math.round((subtotalCents * rate) / 100);
}
