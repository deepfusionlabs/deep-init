import { BaseRepository } from "../core/base";

export class ProductRepository extends BaseRepository {
  findById(id: string) {
    return this.query("products", id);
  }
}
