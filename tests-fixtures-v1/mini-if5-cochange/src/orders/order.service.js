// Order service — orchestrates placing an order.
// This module DOES import the repository below (a real structural edge). The two
// files co-change frequently, but that coupling is legitimate and expected: the
// service is the only caller of the repository, and the import makes the
// dependency explicit. IF-5 must NOT flag this pair as hidden coupling.
const { buildCart } = require('../checkout/cart');
const { computeTax } = require('../billing/tax');
const { saveOrder, findOrder } = require('./order.repository'); // <-- structural edge

function placeOrder(lines) {
  const cart = buildCart(lines);
  const taxCents = computeTax(cart.subtotalCents);

  const order = {
    subtotalCents: cart.subtotalCents,
    shippingCents: cart.shippingCents,
    taxCents,
    totalCents: cart.totalCents + taxCents,
    requiresReview: cart.requiresReview,
    status: 'placed',
  };

  return saveOrder(order);
}

function getOrder(id) {
  const order = findOrder(id);
  if (!order) {
    throw new Error(`Order not found: ${id}`);
  }
  return order;
}

module.exports = { placeOrder, getOrder };
