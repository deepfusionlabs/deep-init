import { BaseService } from "../core/base";

export class AuthService extends BaseService {
  login(user: string) {
    return this.run("auth.login", user);
  }
}
