import express from 'express';
import orderRoutes from './orders/order.routes';
import accountRoutes from './account/account.routes';

const app = express();
app.use(express.json());

app.use('/orders', orderRoutes);
app.use('/account', accountRoutes);

app.get('/health', (_req, res) => res.json({ ok: true }));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`order-api listening on ${PORT}`));

export default app;
