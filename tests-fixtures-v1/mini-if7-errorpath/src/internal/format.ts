// internal/format.ts — consumes formatLabel WITHIN the same component (intra-component,
// not across a boundary), so formatLabel's empty catch is not a cross-boundary swallow.
import { formatLabel } from './helpers';

export function renderLabel(s: string): string {
  return '[' + formatLabel(s) + ']';
}
