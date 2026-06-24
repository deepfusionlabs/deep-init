// order.service.ts — IF-1 false-positive trap cluster.
// The single-order mutators enforce the documented owner-only rule; the look-alikes below
// each OMIT that exact check but are legitimately exempt (a documented suppression mechanism).
// EXACTLY ONE method is a genuine unenforced-rule violation (bulkDeleteOrders).
import { assertOwner } from "../shared/auth";
import { repo, auditLog } from "../shared/repository";

export class OrderService {
  // The documented rule, ENFORCED on the single-delete sibling (the contrast anchor).
  async deleteOrder(userId: string, orderId: string) {
    assertOwner(userId, orderId);            // owner-only rule enforced here
    return repo.delete(orderId);
  }

  // GENUINE VIOLATION (expected fire): the same destructive op, owner-only rule NOT enforced.
  async bulkDeleteOrders(userId: string, orderIds: string[]) {
    return Promise.all(orderIds.map((id) => repo.delete(id)));   // no assertOwner — unenforced
  }

  // TRAP 1 — read-only export: a DIFFERENT operation (no mutation), so the owner-only delete
  // rule does not apply (read-only); must NOT fire.
  async exportOrdersReport(userId: string) {
    return repo.findAllForUser(userId);      // read-only projection, no state change
  }

  // TRAP 2 — equivalent upstream guard: the account-close handler already verified ownership of
  // the whole account before calling this; the per-order check would be redundant (equivalent guard).
  async purgeOnAccountClose(accountVerifiedUserId: string) {
    const ids = await repo.idsForUser(accountVerifiedUserId);    // upstream account-ownership already asserted
    return Promise.all(ids.map((id) => repo.delete(id)));
  }

  // TRAP 3 — documented admin-only bypass: a sanctioned, documented exception (ADR-007) — admins
  // intentionally skip the owner check; must NOT fire.
  async adminForceCancel(adminId: string, orderId: string) {
    // documented/sanctioned admin override (ADR-007) — owner check intentionally bypassed
    return repo.cancel(orderId);
  }

  // TRAP 4 — append-only audit write: an append-only log, never a mutation of an owned order, so
  // the owner-only rule does not apply (append-only); must NOT fire.
  async recordOrderEvent(orderId: string, event: string) {
    return auditLog.append({ orderId, event });   // append-only, frozen records
  }
}
