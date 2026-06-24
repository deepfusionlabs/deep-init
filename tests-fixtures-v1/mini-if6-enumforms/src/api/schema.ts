import { z } from "zod";
// api component — Zod z.enum forms (IF-6 named-set, z.enum form).
export const Channel = z.enum(["email", "sms"]);          // diverges from worker.Channel (missing push) → FIRES
export const LogLevel = z.enum(["debug", "info"]);        // identical to worker.LogLevel → same-value, must NOT fire
