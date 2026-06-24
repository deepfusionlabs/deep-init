import prisma from '../shared/database';
import { adjustStock } from '../products/product.service';
import { getUserById } from '../auth/auth.service';
import { logger } from '../shared/logger';

// BR: Order total = sum of (item price × quantity)
// BR: Order requires valid user
// BR: Each order item must have stock available
// WF: Place order — validate user → check stock per item → create order → deduct stock → return confirmation
export async function placeOrder(userId: string, items: { productId: string; quantity: number }[]) {
  const user = await getUserById(userId);
  if (!user) throw new Error('User not found');

  // Check stock and calculate total
  let total = 0;
  const orderItems = [];
  for (const item of items) {
    const product = await prisma.product.findUnique({ where: { id: item.productId } });
    if (!product) throw new Error(`Product ${item.productId} not found`);
    if (product.stock < item.quantity) throw new Error(`Insufficient stock for ${product.name}`);
    total += product.price * item.quantity;
    orderItems.push({ productId: product.id, quantity: item.quantity, unitPrice: product.price });
  }

  // BR: Minimum order total is $1.00
  if (total < 1.0) throw new Error('Order total must be at least $1.00');

  // Create order and deduct stock in transaction-like flow
  const order = await prisma.order.create({
    data: {
      userId,
      total,
      status: 'confirmed',
      items: { create: orderItems },
    },
    include: { items: true },
  });

  // Deduct stock for each item
  for (const item of items) {
    await adjustStock(item.productId, -item.quantity);
  }

  logger.info('Order placed', { orderId: order.id, userId, total });
  return order;
}

export async function getOrdersByUser(userId: string) {
  return prisma.order.findMany({
    where: { userId },
    include: { items: true },
    orderBy: { createdAt: 'desc' },
  });
}

// BR: Only the order owner can view their orders
export async function getOrder(orderId: string, userId: string) {
  const order = await prisma.order.findUnique({ where: { id: orderId }, include: { items: true } });
  if (!order) throw new Error('Order not found');
  if (order.userId !== userId) throw new Error('Not authorized to view this order');
  return order;
}
