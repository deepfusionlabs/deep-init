import prisma from '../shared/database';
import { logger } from '../shared/logger';

// BR: Product price must be positive
// BR: Product SKU must be unique
// BR: Stock cannot go below zero
export async function createProduct(data: { name: string; sku: string; price: number; stock: number }) {
  if (data.price <= 0) throw new Error('Price must be positive');
  if (data.stock < 0) throw new Error('Stock cannot be negative');
  const existing = await prisma.product.findUnique({ where: { sku: data.sku } });
  if (existing) throw new Error('SKU already exists');
  const product = await prisma.product.create({ data });
  logger.info('Product created', { productId: product.id, sku: product.sku });
  return product;
}

export async function listProducts(page = 1, limit = 20) {
  return prisma.product.findMany({ skip: (page - 1) * limit, take: limit, orderBy: { createdAt: 'desc' } });
}

export async function getProduct(id: string) {
  return prisma.product.findUnique({ where: { id } });
}

// BR: Stock adjustment cannot result in negative stock
export async function adjustStock(productId: string, quantity: number) {
  const product = await prisma.product.findUnique({ where: { id: productId } });
  if (!product) throw new Error('Product not found');
  if (product.stock + quantity < 0) throw new Error('Insufficient stock');
  return prisma.product.update({ where: { id: productId }, data: { stock: product.stock + quantity } });
}
