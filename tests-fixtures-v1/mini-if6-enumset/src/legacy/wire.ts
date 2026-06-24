// legacy/wire.ts — SAME-COMPONENT trap B: …and re-defined here with conflicting membership
// ('cash' vs 'wire'), but BOTH live under the single 'legacy' component. A local no-redeclare
// concern (DD-1/DD-2 linter territory), NOT a cross-component divergence. The >=2-distinct-
// components moat gate suppresses it. Must NOT fire.
export type PayMode = 'card' | 'wire';
