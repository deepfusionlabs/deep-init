import { sendEmail, sendSms } from './providers';
import { logger } from '../shared/logger';

export interface NotificationJob {
  channel: 'email' | 'sms';
  to: string;
  template: string;
  data: Record<string, unknown>;
}

const pending: NotificationJob[] = [];

// ADR-001: the ONLY sanctioned dispatch path. Enqueue and return immediately;
// the worker drains the queue asynchronously so request handlers never block
// on a provider.
export function enqueue(job: NotificationJob): void {
  pending.push(job);
}

// Drained out-of-band by the worker process (not on the request path).
export async function drainOnce(): Promise<void> {
  const job = pending.shift();
  if (!job) return;
  try {
    if (job.channel === 'email') {
      await sendEmail(job.to, job.template, job.data);
    } else {
      await sendSms(job.to, job.template, job.data);
    }
  } catch (err) {
    logger.error('notification dispatch failed; will retry', { job, err });
    pending.push(job);
  }
}

export const NotificationQueue = { enqueue, drainOnce };
