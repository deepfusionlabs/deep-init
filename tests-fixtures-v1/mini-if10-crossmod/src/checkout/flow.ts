import { NEW_CHECKOUT } from '../flags';
export function checkout() {
  if (NEW_CHECKOUT) {
    return runNew();
  }
  return runLegacy();
}
function runNew() { return 1; }
function runLegacy() { return 0; }
