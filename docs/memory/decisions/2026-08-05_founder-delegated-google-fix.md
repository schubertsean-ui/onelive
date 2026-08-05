# Decision: founder-delegated Google credential intervention (2026-08-05)

**Founder, verbatim (session chat, after five mechanically-verified failed
key/config re-pastes on the Custom Search lane):**

> "you fix this - I give you limited timeframe permission to fix this"

and, on the method (rejecting further blind console click-paths):

> "you know this is the icorrect way to provide me with instructions. Do it
> correctly."

**What was authorized and done.** A short-lived OAuth sign-in (standard
Google Cloud SDK flow, PKCE, founder-approved in browser; token held only in
session memory, ~1h expiry). Under it, by API only: created scratch project
`onelive-search-8b3c7d`; enabled customsearch.googleapis.com on it and
verified ENABLED on `live-504600` (the project the console displays as
"1live"); minted two API keys restricted to Custom Search only (one per
project); probed the live endpoint with both, plus with Google's own
documented example engine id; checked billing accounts (one exists, open),
attempted linking it to the scratch project (refused: FAILED_PRECONDITION /
QuotaFailure — the account's project-link quota), and read effective quotas
(100/day granted for Custom Search on the scratch project).

**Findings (all mechanical, none inferred).**
1. The CX (`707d7bec86b814566`, engine "1live discovery") is correct, and
   the engine's "Search the entire web" was OFF until the founder enabled it
   this session — a real misconfiguration for discovery, fixed, but NOT the
   403's cause.
2. Every key × every project × both engines returns the identical
   `403 PERMISSION_DENIED: "This project does not have the access to Custom
   Search JSON API"` — including a brand-new project + fresh key created
   seconds earlier by API. The refusal is therefore **account-level, on
   Google's side**, and not fixable by any key/project/engine configuration
   available to us.
3. The account holds FIVE OneLive-ish Cloud projects (`live-504600`,
   `onelive-504201`, `onelive-502015`, `gen-lang-client-0939367588`, plus
   the scratch one) — recorded here because the console's project picker
   shows display names, not ids, and this ambiguity burned hours.

**Cleanup (account left as found).** Both agent-created keys deleted, the
scratch project delete-requested, the OAuth token and all key material
destroyed at the end of the granted window. No billing change was made.

**Standing state.** GOOGLE_CSE_KEY currently holds the founder's fresh
`New 1live-search` key (well-formed; unusable until Google lifts the
account-level refusal). Resolution paths, founder-owned: a Google support
ticket / Custom Search help-community post citing the exact error above, or
a different Google account. Switching the search lane to another licensed
provider (e.g. Brave Search API) is a NEW SERVICE + MONEY decision:
founder-crucial, proposed separately, never agent-decided.
