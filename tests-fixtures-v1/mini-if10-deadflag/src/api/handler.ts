// api/handler.ts — MIXED-CONDITION trap: MODE is a compile-time const, but the conditional also
// tests a runtime term (user.isAdmin), so the literal does not statically decide the branch. The
// sole-operand anchor never matches a mixed test → predicate FALSE. Must NOT fire.
const MODE = 'on';

export function handle(user: { isAdmin: boolean }): void {
  if (MODE === 'on' && user.isAdmin) {
    grant();
  }
}
declare function grant(): void;
