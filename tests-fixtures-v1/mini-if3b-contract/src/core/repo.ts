// core/repo public surface: exports fetchUser ONLY. fetchOrders is NOT exported (no such symbol).
export function fetchUser(id: string) {
  return { id, name: 'user-' + id };
}

// private helper — not part of the public surface
function _hydrate(row: any) {
  return row;
}
