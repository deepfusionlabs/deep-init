// jobs/status.ts — HOMONYM trap B: a job-runner Status. Same name as ui/Status but ZERO shared
// members → a coincidental homonym, not a divergent copy of one concept (the >=1-shared-member
// gate treats them as unrelated). Must NOT fire.
export type Status = 'queued' | 'running' | 'done';
