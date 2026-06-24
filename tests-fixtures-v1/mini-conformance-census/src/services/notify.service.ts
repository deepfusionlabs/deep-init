import { BaseService } from "../core/base";

export class NotifyService extends BaseService {
  send(to: string) {
    return this.run("notify.send", to);
  }
}
