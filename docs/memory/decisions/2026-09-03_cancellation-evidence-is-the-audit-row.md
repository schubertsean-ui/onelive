# A cancellation's evidence is the audit row — no candidate is invented for it

**Founder-ratified 2026-09-03.** Verbatim:

> Cancel evidence: audit_log plus the defining URL and the reason is enough for
> v1. Do not invent a candidate_evidence row with no candidate. Title stays
> unwritten until we have a permalink (R-095). That is correct.

## The question, and who asked it

The adversarial panel raised it on PR #214 r3 as a NIT, explicitly not
blocking, and referred it to the founder rather than calling it a defect:

> mark-gone decisions do not create a `candidate_evidence` row because
> `matched_candidate_id` is absent; audit still records the mutation, so I am
> not blocking on this, but the founder should confirm that audit-only
> evidence is the intended trust record for cancellations.

It is a fair question because the two mutation kinds are asymmetric on
purpose and the asymmetry is easy to mistake for an oversight:

- An **update** has a matched candidate — the listing on the page that stated
  the new time — so it writes a `candidate_evidence` row quoting that page
  alongside its `audit_log` row.
- A **mark-gone** has no matched candidate, by definition. The evidence IS the
  absence. There is nothing on the page to point at.

## The ruling, and why it is the right shape

Audit-only, and the asymmetry is ratified rather than tolerated. The
`audit_log` row already carries everything a person auditing a cancellation
needs: the run id, the defining page URL, the source, the fields changed, and
the reason in plain words (`worker/listing_update.py::apply_decisions`).

The alternative would have been to synthesise a `candidate_evidence` row for a
candidate that does not exist. That is worse than incomplete — it is a
fabricated attestation, and the whole point of an evidence row is that
something real stood behind it. A cancellation's honest record is "we read
this page at this time and it no longer named this listing", which is exactly
what the audit row says.

## Also confirmed in the same directive

`title` stays unwritten until a stable per-listing identifier exists (R-095).
A rename and a replacement are indistinguishable on same-page evidence alone,
and one of those two outcomes puts a fabricated name on a public listing.
