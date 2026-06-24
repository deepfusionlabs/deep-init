// Order repository — owns persistence of Order rows. In-memory for the fixture.
const ORDERS = new Map();
let nextId = 1;

function saveOrder(order) {
  const id = `ord-${nextId++}`;
  const stored = { id, ...order, createdAt: new Date().toISOString() };
  ORDERS.set(id, stored);
  return stored;
}

function findOrder(id) {
  return ORDERS.get(id) || null;
}

function allOrders() {
  return Array.from(ORDERS.values());
}

module.exports = { saveOrder, findOrder, allOrders };
