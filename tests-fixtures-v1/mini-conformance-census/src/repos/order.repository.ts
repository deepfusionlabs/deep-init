import { BaseRepository } from "../core/base";

export class OrderRepository extends BaseRepository {
  findById(id: string) {
    return this.query("orders", id);
  }
}
