// payments component — TS enum forms (IF-6 named-set, enum form).
export enum Priority { Low, High }          // diverges from billing.Priority (missing Med) → FIRES
export enum Mode { On, Off }                // identical to billing.Mode → same-value, must NOT fire
