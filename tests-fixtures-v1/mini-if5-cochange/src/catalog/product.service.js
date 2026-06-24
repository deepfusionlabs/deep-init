// Product catalog service — simple in-memory lookup used by the cart.
const CATALOG = {
  'sku-1': { id: 'sku-1', name: 'Widget', priceCents: 1999 },
  'sku-2': { id: 'sku-2', name: 'Gadget', priceCents: 14999 },
  'sku-3': { id: 'sku-3', name: 'Gizmo', priceCents: 4999 },
};

function getProduct(productId) {
  const product = CATALOG[productId];
  if (!product) {
    throw new Error(`Unknown product: ${productId}`);
  }
  return product;
}

module.exports = { getProduct };
