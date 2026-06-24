// billing component — TS enum forms.
export enum Priority { Low, Med, High }     // has Med; payments.Priority lacks it → divergent membership
export enum Mode { On, Off }                // identical to payments.Mode → same-value clone, must NOT fire
