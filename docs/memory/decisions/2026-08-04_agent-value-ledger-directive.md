# Decision — Owned Agent clients get a value ledger + weekly ROI in THEIR shared Excel (founder-directed)

One-line: founder-directed — the 1Live Owned Agent (the client-facing agent product) keeps a per-client value ledger of every task it performs for a business (hours saved, $ value) in the CLIENT's shared Excel workbook and sends a weekly "you saved $" ROI report to the client's contact; visible ROI is the retention strategy, free work the referral engine.

**Date:** 2026-08-04. **Authority:** founder-directed, verbatim (message titled "Re: AI Agent…."):

> *"Give the agent a value ledger. It logs every task and sends a weekly ROI report to the contact: hours saved, $ value*
> *Put the agent in the group chat.*
> *Uptime is a selling point.*
> *Free work is the referral engine.*
> *Make the agent write to Excel, not its own markdown. A shared source of truth is the difference between a demo and a system.*
> *Visible ROI is the retention strategy. A weekly "you saved $" report."*

**Subject clarified by the founder same day (verbatim):** *"This was to be applied to the AI Agent we've built not to this org or to me. Good gosh, review the canon and repo."* — the subject is the **Owned Agent product** (`docs/strategy/ONE_LIVE_OWNED_AGENT_v1.md` + AGENT_SURFACES + CONNECTOR_REGISTRY + `brain/pipeline/`); "the contact" is the client business's contact person. The first build of this directive aimed it at the repo's agent org reporting to the founder — a founder-caught ESCAPE (Kaizen row + red class `directive-subject-assumed`, 2026-08-04): an ambiguous directive subject is a QUESTION before building, never an interpretation note shipped with the wrong build.

## What was built (Contract #43, PR #159, corrected same day)

- **The client value ledger ENGINE** — `tools/value_ledger.py`: logs every task the agent performs for a business into that client's Excel workbook (`--path` per client; owner-editable blended hourly rate in the workbook's Config sheet), maintains the "Weekly ROI" sheet (per-week tasks/hours/$ + cumulative), prints the weekly "you saved $" report for the contact, and regenerates a deterministic CSV audit mirror. Every $ figure is an estimate (hours x rate) and says so; every row requires its estimate basis; rates freeze per row; non-finite/negative numbers, malformed dates, and tampered schemas refuse loudly. Hermetic tests.
- **Committed demo** — `docs/strategy/examples/AGENT_CLIENT_VALUE_LEDGER_DEMO.xlsx` (+ mirror): one unmistakably-illustrative row ("DEMO (illustrative): …", session `demo-seed`), pinned by test so it can never read as live client work (claim-ledger discipline). No real client data exists or is claimed.
- **Canon integration** — dated addendum in `ONE_LIVE_OWNED_AGENT_v1.md` (the directive verbatim + the three-layer mapping); two new PLANNED connector rows in `ONE_LIVE_CONNECTOR_REGISTRY_v1.md` (client shared spreadsheet — AUTHORIZED SYNC; client team group chat — DIRECT PUBLISH via their invite).

## Still gated (no license added)

Owned Agent Phase A/B/C gates and Q1–Q22 stand unchanged. The spreadsheet-sync and group-chat connectors are PLANNED like every other connector: platform credentials, OAuth apps, and any sending/scheduled delivery are founder-crucial (new services; Sentinel dead-man + caps before any scheduled loop). An external "uptime" claim enters the claim ledger with evidence before appearing in copy.

## Posture captured (business canon, no code)

"Uptime is a selling point" and "free work is the referral engine" are recorded as go-to-market posture for the Owned Agent — consistent with free-forever (Q4) and no-connect-to-rank; inputs to the pilot design, not build orders.
