// EmailGateway does NOT implement Retryable. ADR-104 is class-ranging with a
// structural check, but the gateway class has only 2 members (N<3) — no
// majority can exist, so the census DEGRADES (emits nothing) rather than guess.
export class EmailGateway {
  send(to: string) {
    return to;
  }
}
