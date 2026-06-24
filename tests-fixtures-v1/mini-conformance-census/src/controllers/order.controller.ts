// ADR-103 is class-ranging ("every controller") but its required property —
// "cohesive / single-responsibility" — has no decidable structural check, so
// the census DEGRADES (it never guesses a conformance fact it cannot compute).
export class OrderController {
  place() {
    return "placed";
  }
}
