// ADR-102 is a CARDINALITY-1 decision about this one component — it does not
// quantify over a class of siblings, so the census overlay does not apply
// (there is no population to enumerate). A contradiction here is plain IF-4.
import { createClient } from "redis";

export const cache = createClient();
