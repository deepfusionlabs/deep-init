// BREACH: imports fetchOrders from core/repo, but core/repo does not export fetchOrders.
// (fetchUser IS exported — that part of the import is valid.)
import { fetchUser, fetchOrders } from '../core/repo';

export function load(id: string) {
  return [fetchUser(id), fetchOrders(id)];
}
