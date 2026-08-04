# Decision — Agent Value Ledger: log every task, weekly ROI in shared Excel (founder-directed)

One-line: founder-directed — the agent keeps a value ledger of every task (hours saved, $ value) in a SHARED Excel workbook (never agent-private markdown) and produces a weekly "you saved $" ROI report; visible ROI is the retention strategy.

**Date:** 2026-08-04. **Authority:** founder-directed, verbatim (message titled "Re: AI Agent…."):

> *"Give the agent a value ledger. It logs every task and sends a weekly ROI report to the contact: hours saved, $ value*
> *Put the agent in the group chat.*
> *Uptime is a selling point.*
> *Free work is the referral engine.*
> *Make the agent write to Excel, not its own markdown. A shared source of truth is the difference between a demo and a system.*
> *Visible ROI is the retention strategy. A weekly "you saved $" report."*

## What was built (Contract #43, same day)

- `tools/value_ledger.py` + `docs/metrics/AGENT_VALUE_LEDGER.xlsx` (canonical, founder-editable — the hourly rate lives in its Config sheet, shipped as a LABELED $150/h placeholder for the founder to set) + `AGENT_VALUE_LEDGER.csv` (deterministic audit mirror so the binary xlsx stays reviewable in git and by the evaluator) + hermetic tests.
- Every entry: date · session · task · category · hours_saved · **estimate_basis (required — an estimate with no stated basis is refused)** · the rate it was logged under (frozen per row) · value_usd = hours x rate in Decimal cents. Non-finite/negative numbers, malformed dates, and tampered schemas refuse loudly.
- `report --as-of` prints the weekly + cumulative "you saved $" summary in plain language, always labeled as estimates.
- **No historical backfill**: retro-estimating hours for past merged PRs would manufacture numbers with no recorded basis. The ledger measures honestly from its first entry forward.

## Interpretation on the record (correctable, not asserted as founder words)

The directive's "the agent" is read as THIS repo's agent org and "the contact" as the founder. If the founder meant a different venture/deployment (e.g. a client-facing agent product), the tool is deliberately generic — `--path` points it at any workbook — and the reading should be corrected, not defended.

## Actioned vs founder-crucial (the send half stays a decision)

- **Actioned:** logging + weekly report GENERATION + shared-Excel source of truth (this build).
- **Founder-crucial, NOT actioned** (new services / external comms / scheduled loops per charter — consolidated in the PR ask list): (1) the weekly SEND channel (email or group chat delivery, and any scheduled runner — Sentinel rule: dead-man ping + caps before any cron); (2) "put the agent in the group chat" (a new outward-facing surface + credentials); (3) the real hourly rate (founder edits Config!B1).

## Posture notes captured (business canon, no code)

"Uptime is a selling point" and "free work is the referral engine" are recorded here as founder go-to-market posture for agent work — inputs to future venture/Owned-Agent decisions, not build orders.
