import { ROLLOUT } from '../flagdefs/defs';
export function view() {
  const ROLLOUT = loadRollout();
  if (ROLLOUT) {
    return showRollout();
  }
  return null;
}
function loadRollout() { return Math.random() > 0.5; }
function showRollout() { return 1; }
