# Fix-library taxonomy

Failure-agnostic. Use this at process steps 5 and 6.
Does not belong to Ticket B.

Every library entry is tagged on four axes.

## 1. Symptom (what you see)

- live-miss — live system is not Success
- view-hide — rows exist but a view does not show them
- catalog-hole — trusted door printed it; we have no row
- ingest-crash — the write job dies
- deploy-miss — master changed; live did not
- stub — a real module was replaced by a pointer or empty file
- import-break — a name the job imports is missing
- test-lie — a test requires a value the door did not print
- law-drift — a rule file contradicts the current Process

## 2. Layer (where it lives)

- reader — how a door is read
- writer — how a row is planned and written
- view — how live pages filter and show
- ingest — the job that walks doors
- deploy — master → live site
- library — this catalog of fixes
- automation — scheduled or event bots

## 3. Cause (one why)

- invented-value — we stamped a clock, duration, or field the door did not print
- missing-name — import / function / file name does not exist
- wrong-gate — a filter decided catalog membership
- clock-as-identity — a view word used as a stored key
- utc-vs-locale — a date moved because of timezone math
- stub-shipped — SEE_FILE or empty module on master
- success-undefined — step 3 was skipped

## 4. Scope

- universal — any locale, any ticket
- pack — one locale pack only

## How to tag a new entry

`FL-NNN` + symptom + layer + cause + scope + success probe from step 3 + SHA + step-11 result.
