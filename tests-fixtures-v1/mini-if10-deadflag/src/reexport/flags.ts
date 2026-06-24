// reexport/flags.ts — DETACHED RE-EXPORT trap: FLAG is exported via a separate `export { FLAG }`
// statement (not `export const`). It is a cross-module contract, so — per the exported-flag rule —
// it must suppress even though the local arm looks dead. Must NOT fire.
const FLAG = false;
export { FLAG };

export function gate(): string {
  if (FLAG) {
    return dead();
  }
  return ok();
}
declare function dead(): string;
declare function ok(): string;
