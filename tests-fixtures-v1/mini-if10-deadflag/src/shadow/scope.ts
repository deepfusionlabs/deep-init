// shadow/scope.ts — SHADOWING trap: an inner `const FLAG = true` shadows the outer module-level
// `const FLAG = false`. A flat regex can't resolve scope, so >1 const binding of the same name is
// ambiguous → skip entirely (precision-safe). The inner `if (FLAG)` arm is actually REACHABLE (inner
// FLAG is true), so firing would assert a live arm is dead — exactly the FP to avoid. Must NOT fire.
const FLAG = false;

export function outer(): string {
  return inner();
}

function inner(): string {
  const FLAG = true;
  if (FLAG) {
    return reached();
  }
  return never();
}
declare function reached(): string;
declare function never(): string;
