import { logger } from '../shared/logger';

// Slow, flaky external providers. ADR-001 exists precisely because these can
// hang or fail; they must never be called inline on a request path.

export async function sendEmail(
  to: string,
  template: string,
  data: Record<string, unknown>,
): Promise<void> {
  // Simulated network call to the email provider.
  await new Promise((resolve) => setTimeout(resolve, 50));
  logger.info('email sent', { to, template, data });
}

export async function sendSms(
  to: string,
  template: string,
  data: Record<string, unknown>,
): Promise<void> {
  // Simulated network call to the SMS provider.
  await new Promise((resolve) => setTimeout(resolve, 50));
  logger.info('sms sent', { to, template, data });
}
