import { z } from "zod";
// worker component — Zod z.enum forms.
export const Channel = z.enum(["email", "sms", "push"]);  // has push; api.Channel lacks it → divergent membership
export const LogLevel = z.enum(["debug", "info"]);        // identical to api.LogLevel → same-value clone, must NOT fire
