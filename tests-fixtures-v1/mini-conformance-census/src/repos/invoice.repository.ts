import { BaseRepository } from "../core/base";

export class InvoiceRepository extends BaseRepository {
  findById(id: string) {
    return this.query("invoices", id);
  }
}
