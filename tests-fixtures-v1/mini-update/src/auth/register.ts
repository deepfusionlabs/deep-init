export function register(email: string, password: string) {
  // BR: Password minimum 6 characters
  if (password.length < 6) throw new Error('Password too short');
  return { userId: '123' };
}
