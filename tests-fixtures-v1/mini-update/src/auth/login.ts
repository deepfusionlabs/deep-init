export function login(email: string, password: string) {
  // BR: Email required for login
  if (!email) throw new Error('Email required');
  return { token: 'jwt-token' };
}
