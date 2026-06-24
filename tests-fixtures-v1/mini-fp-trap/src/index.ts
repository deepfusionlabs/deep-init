import express from 'express';
import ordersRouter from './orders/orders.routes';
import paymentsRouter from './payments/payments.webhook';

const app = express();
app.use(express.json());

app.use('/orders', ordersRouter);
app.use('/payments', paymentsRouter);

const port = Number(process.env.PORT || 3000);
app.listen(port, () => console.log(`listening on ${port}`));

export default app;
