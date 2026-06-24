// checkout/flow.ts — NEW_CHECKOUT is a compile-time-constant false; the if-true arm never runs.
const NEW_CHECKOUT = false;

export function checkout(): string {
  if (NEW_CHECKOUT) {
    return runNewFlow(); // statically-dead arm (NEW_CHECKOUT can never be true)
  }
  return runLegacyFlow();
}

function runNewFlow(): string { return 'new'; }
function runLegacyFlow(): string { return 'legacy'; }
