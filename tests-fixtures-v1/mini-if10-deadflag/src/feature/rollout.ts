// feature/rollout.ts — EXPORTED trap: ROLLOUT is exported — a cross-module contract another
// component may read (and whose meaning we can't confirm constant from this file alone). The
// cross-module const elevation is the deferred semantic part. Must NOT fire.
export const ROLLOUT = false;

export function maybeRollout(): void {
  if (ROLLOUT) {
    rollout();
  }
}
declare function rollout(): void;
