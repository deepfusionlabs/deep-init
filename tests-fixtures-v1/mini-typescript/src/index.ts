import express from 'express';
import rateLimit from 'express-rate-limit';
import authRoutes from './auth/auth.routes';
import productRoutes from './products/product.routes';
import orderRoutes from './orders/order.routes';
import { logger } from './shared/logger';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// BR: Rate limiting — 100 requests per 15 minutes per IP
const limiter = rateLimit({ windowMs: 15 * 60 * 1000, max: 100 });
app.use(limiter);

app.use('/auth', authRoutes);
app.use('/products', productRoutes);
app.use('/orders', orderRoutes);

// IP: Health check endpoint for monitoring
app.get('/health', (_, res) => res.json({ status: 'ok', timestamp: new Date().toISOString() }));

app.listen(PORT, () => logger.info(`Server started on port ${PORT}`));
