// Order domain types + persistence (stub).
export interface Order {
  id: string;
  customerEmail: string;
  totalCents: number;
  status: "pending" | "placed" | "paid";
}
export async function save(order: Order): Promise<void> { void order; }

export interface Tx {
  insert(table: string, row: unknown): Promise<void>;
  commit(): Promise<void>;
  rollback(): Promise<void>;
}
