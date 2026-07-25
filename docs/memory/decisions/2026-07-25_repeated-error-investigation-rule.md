# 2026-07-25 — Repeated-error investigation rule (founder-directed, global)

**Directive (founder, verbatim, 2026-07-25, session `onelife-meta-carousel`):**
"If you get the same error or message more than twice you prob need to
investigate because there's probably an error." Followed by the
globalization directive, verbatim: "Something like this needs to be a
global adopted condition 'the recurring "exceeds maximum tokens" on every
poll deserved investigation instead of a workaround.'"

## The rule (encoded in docs/OPERATING_RULES.md §1)

The same error/warning/anomalous message occurring more than twice is a
DEFECT SIGNAL requiring root-cause investigation before or alongside any
workaround. The investigation must produce a recorded determination:
our defect / upstream defect / justified accepted-cost workaround.
Routinizing a recurring error without that recorded determination is
itself the defect.

## The instance that produced it

During the PR #63/#65 CI-delivery incident, every 3-minute recovery poll
hit "result exceeds maximum allowed tokens" from the GitHub MCP
`actions_list` tool; the agent workaround-ed it (dump file → grep) for
~15 cycles without investigating. Founder flagged it; investigation took
one experiment and found a REAL defect: the MCP server ignores its own
`per_page` and `minimal_output` parameters for `list_workflow_runs`,
always returning the full ~420KB run history. Determination: upstream
tool defect; the dump→grep workaround is the justified accepted cost;
data verified live per poll. The lesson the rule encodes: the workaround
was fine, the SILENT routinization of it was not.

## Scope

OneLive-binding immediately (OPERATING_RULES §1). Global per the
founder's directive: applies to every project adopting the universal
kernel — queued as a kernel amendment note (the kernel doc's ratified
scope is "as merged in PR #61", so the text lands there as a
founder-directed amendment at its next revision, citing this record).

## Kaizen

founder(Red) catch, class: routinized-recurring-error. Counter-measure:
this rule + the recorded-determination requirement. Escape definition:
any future session found to have repeated the same error 3+ times
without a recorded root-cause determination.
