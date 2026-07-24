// Pure feed-shaping logic — unit-tested so the "nothing is silently hidden"
// invariant holds structurally, not by inspection of the JSX.
//
// The trust rule (evaluator PR #59) applies to the RENDERED surface, not just
// the query: every fetched event must land in a rendered domain bucket, and no
// per-domain cap may drop rows. A `disputed` event in an unknown category, or
// in position 13, must still be shown.

import { DOMAINS, DOMAIN_LABEL, type DomainMeta } from "./domains";
import type { LicensedEvent } from "./licensed";

// Fold any category that is null or outside the taxonomy into "unmapped"
// ("Other") — taxonomy drift can never silently omit a row.
export function normalizeDomain(category: string | null): string {
  return category && DOMAIN_LABEL.has(category) ? category : "unmapped";
}

export type DomainGroup = { domain: DomainMeta; items: LicensedEvent[] };

// Group every event under a rendered domain, in DOMAINS order, preserving count:
// the sum of items across groups always equals events.length (proven in tests).
export function groupByDomain(events: LicensedEvent[]): DomainGroup[] {
  const byId = new Map<string, LicensedEvent[]>();
  for (const e of events) {
    const id = normalizeDomain(e.category);
    const arr = byId.get(id);
    if (arr) arr.push(e);
    else byId.set(id, [e]);
  }
  const groups: DomainGroup[] = [];
  for (const d of DOMAINS) {
    const items = byId.get(d.id);
    if (items && items.length) groups.push({ domain: d, items });
  }
  return groups;
}
