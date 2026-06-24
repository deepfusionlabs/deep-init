import { BaseService } from "../core/base";

export class CatalogService extends BaseService {
  list() {
    return this.run("catalog.list", null);
  }
}
