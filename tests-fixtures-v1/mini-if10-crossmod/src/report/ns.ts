import * as F from '../flags';
export function ns() {
  if (F.NEW_CHECKOUT) { return 1; }
  return 0;
}
