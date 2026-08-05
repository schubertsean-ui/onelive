# Decision: search lane switches to the Brave Search API — founder-ratified (2026-08-05)

**Founder, verbatim (session chat, immediately after the Google verdict was
reported with the Brave option and its cost stated):**

> "Switch to Brave - do all the work"

**Context.** Google's Custom Search JSON API refuses every project on the
founder's Google account at the account level — proven mechanically under a
founder-delegated API intervention (fresh project + fresh key created by API,
identical 403, Google's own example engine also refused; full trail in
2026-08-05_founder-delegated-google-fix.md). The search lane (source scanner
+ Eventbrite organizer discovery) was its only dependent. The founder was
offered a Google support ticket vs. a provider switch with the cost stated
(~$3–5/month at our volume if the free tier is outgrown) and ratified the
switch — this record is the new-service + money authorization.

**What changed (all in the same PR as this record).**
- `tools/search_api.py` (new): shared Brave Web Search client — documented
  endpoint, keyed access via repo secret BRAVE_SEARCH_API_KEY, 1 req/s
  throttle enforced in code, fail-loud MissingKey/SearchError contract.
- `tools/scan_new_sources.py` + `tools/search_discover_eventbrite.py`:
  query through the shared client; identical custody (candidates for human
  curation only), identical fail-loud exits (2 missing key / 3 empty).
- `provider-dryrun.yml` (eventbrite-search, source-scan) and
  `ops-diagnostics.yml` (cse-probe → brave-probe, key-shape line kept):
  BRAVE_SEARCH_API_KEY replaces the GOOGLE_CSE_KEY/GOOGLE_CSE_CX pair.
- `docs/ops/SEARCH_QUOTA_BUDGET.md` v2: 2,000/month budget replaces the
  100/day Google split; paid-tier raises stay founder-crucial.

**Standing state after merge.** The lane is fail-closed until the founder
creates the key (Free plan) at https://api-dashboard.search.brave.com/ and
adds repo secret BRAVE_SEARCH_API_KEY. GOOGLE_CSE_KEY/GOOGLE_CSE_CX become
inert; founder may delete them at leisure. The Google account-level refusal
remains documented for any future revisit; no Google support ticket is filed
unless the founder chooses to.
