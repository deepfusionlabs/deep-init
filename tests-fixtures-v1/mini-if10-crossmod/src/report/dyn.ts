export async function dyn() {
  const { NEW_CHECKOUT } = await import('../flags');
  if (NEW_CHECKOUT) { return 1; }
  return 0;
}
