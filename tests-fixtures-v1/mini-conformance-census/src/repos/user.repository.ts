import { BaseRepository } from "../core/base";

export class UserRepository extends BaseRepository {
  findById(id: string) {
    return this.query("users", id);
  }
}
