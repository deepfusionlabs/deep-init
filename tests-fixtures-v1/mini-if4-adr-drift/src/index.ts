import express from 'express';
import { placeOrder, cancelOrder } from './orders/order.service';
import { loadConfig } from './config/loader';
import { NotificationQueue } from './notifications/queue';
import { logger } from './shared/logger';

async function main() {
  const config = await loadConfig('./config.json');
  const app = express();
  app.use(express.json());

  app.post('/orders', async (req, res) => {
    const order = await placeOrder(req.body);
    res.status(201).json(order);
  });

  app.post('/orders/:id/cancel', async (req, res) => {
    await cancelOrder(req.params.id, req.body.email);
    res.status(202).end();
  });

  // Out-of-band queue worker tick.
  setInterval(() => void NotificationQueue.drainOnce(), 100);

  app.listen(3000, () => logger.info('listening', { concurrency: config.queueConcurrency }));
}

void main();
