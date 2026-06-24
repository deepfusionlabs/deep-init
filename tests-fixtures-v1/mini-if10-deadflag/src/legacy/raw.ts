// legacy/raw.ts — BARE-LITERAL trap: a bare `if (false)` with NO const indirection. This is ESLint
// no-constant-condition's job, not IF-10's — the absent const-binding is exactly the linter-silence
// gap IF-10 is defined against (IF-10 fires only when a const indirection makes the linter go quiet).
// Must NOT fire.
export function raw(): string {
  if (false) {
    return dead();
  }
  return ok();
}
declare function dead(): string;
declare function ok(): string;
