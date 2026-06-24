// feature/toggle.ts — LET+REBIND trap: ENABLED is `let` and reassigned at runtime — not a
// compile-time constant (its value provably changes before the test). Must NOT fire.
let ENABLED = false;

export function init(): void {
  ENABLED = loadFlag();
  if (ENABLED) {
    runFeature();
  }
}
declare function loadFlag(): boolean;
declare function runFeature(): void;
