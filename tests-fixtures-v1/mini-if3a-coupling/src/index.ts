import { ordersRoutes } from './orders/orders.routes';
import { inventoryRoutes } from './inventory/inventory.routes';

// Tiny route registry wiring both domains together. The application only
// composes the two domains' routes — it does not mediate their data access.
export const routes = {
  ...ordersRoutes,
  ...inventoryRoutes,
};

export default routes;
