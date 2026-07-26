# Founder setup — explicit steps, not summaries

**Standing rule (founder directive, 2026-07-26, verbatim: "Never make me
ask again for Explicit 'how to' step by step").** Any time the founder is
asked to do something, the ask ships as click-by-click steps: the exact
URL, the exact button text, the exact field name, and what to paste. A
bullet naming a task without its steps is a defect, not a summary. This
supersedes brevity and applies to every report, PR description, and
escalation. CLAUDE.md's communication rule 5 already said this; it was
violated repeatedly during the 2026-07-26 session, which is why it now
has its own file and its own runbook below.

Format each ask like the sections here: numbered, one action per line,
phone-friendly, with the copy-paste value spelled out.

---

## 1. Meta credentials — the only hard blocker to live carousels

Result: three secrets in GitHub — `META_ACCESS_TOKEN`, `META_IG_USER_ID`,
`META_FB_PAGE_ID`. Budget 30–45 minutes the first time.

**If a label has moved:** Meta renames menu items often. Do NOT guess at
a similar-looking option — screenshot the screen you are stuck on, send
it to Claude, and get the corrected step back. Guessing in a permissions
dialog is how an account ends up with the wrong scopes granted, and the
whole point of this file is that you never have to improvise.

### 1a. Make the Instagram account publishable (5 min)

1. Open Instagram on your phone → your profile → the ☰ menu (top right).
2. Tap **Settings and privacy**.
3. Tap **Account type and tools** → **Switch to professional account**.
4. Choose **Business** (not Creator — Creator accounts cannot use the
   content-publishing API).
5. When it offers to connect a Facebook Page, connect one. If you have no
   Page, create one at https://www.facebook.com/pages/create — any name,
   any category; it exists to hold the API permission.

### 1b. Create the Meta app (10 min)

1. Go to https://developers.facebook.com/apps
2. Click **Create app**.
3. If asked "What do you want your app to do?", choose **Other**.
4. For app type choose **Business**. Click **Next**.
5. Name it `OneLive Posting`. Enter your email. Click **Create app** and
   re-enter your password if prompted.
6. On the app dashboard, find **Instagram** in the product list and click
   **Set up**.

### 1c. Get the access token (10 min)

1. Go to https://developers.facebook.com/tools/explorer
2. Top right, set **Meta App** to `OneLive Posting`.
3. Set **User or Page** to **User token**.
4. Click **Add a Permission** and tick all five:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
   - `business_management`
5. Click **Generate Access Token**. Approve the popup, selecting the
   Instagram account and Page from step 1a.
6. Copy the token that appears. It is short-lived — step 1d fixes that.

### 1d. Make the token long-lived (5 min)

1. Still in Graph API Explorer, click the **ⓘ** icon next to the token.
2. Click **Open in Access Token Tool**.
3. Click **Extend Access Token** at the bottom.
4. Copy the new token. **This is your `META_ACCESS_TOKEN`.** It lasts
   about 60 days; calendar a reminder to repeat 1c–1d before it expires.

### 1e. Find the two IDs (5 min)

1. Back in https://developers.facebook.com/tools/explorer, paste your
   long-lived token into the **Access Token** box.
2. In the query box, replace whatever is there with exactly:
   ```
   me/accounts
   ```
   Click **Submit**. In the response find your Page and copy its `id`.
   **That is your `META_FB_PAGE_ID`.**
3. Now query, replacing `PAGE_ID` with the number you just copied:
   ```
   PAGE_ID?fields=instagram_business_account
   ```
   Click **Submit**. The response contains
   `"instagram_business_account": {"id": "17841…"}`. Copy that inner id.
   **That is your `META_IG_USER_ID`.**

### 1f. Store all three in GitHub (3 min)

1. Go to https://github.com/schubertsean-ui/onelive/settings/secrets/actions
2. Click **New repository secret**.
3. Name: `META_ACCESS_TOKEN` — Secret: paste the long-lived token from
   1d. Click **Add secret**.
4. Repeat for `META_FB_PAGE_ID` (the value from 1e step 2).
5. Repeat for `META_IG_USER_ID` (the value from 1e step 3).
6. Confirm all three appear in the list. Tell Claude "Meta credentials
   added" — that fires R-026 and unlocks the posting client.

---

## 2. `ONELIVE_APPROVAL_KEY` — signs your carousel approvals

This is the secret that makes an approval provably yours. Without it, no
post can be signed, so nothing can publish even with Meta connected.

1. Generate a random key. On a Mac, open Terminal and run:
   ```
   openssl rand -base64 48
   ```
   Copy the output. If you have no terminal handy, use
   https://1password.com/password-generator set to **64 characters** with
   letters, numbers and symbols all on — that lands near the ~256 bits of
   entropy `openssl rand -base64 48` gives you. Do not shorten it.
2. Go to https://vercel.com/sss-projects-e4775771/onelive/settings/environment-variables
3. Click **Add New** (or **Create new**).
4. Key: `ONELIVE_APPROVAL_KEY`
5. Value: paste the generated key.
6. Environments: tick **Production ONLY**. Untick Preview and
   Development — a signing key in Preview is a signing key on a public
   URL.
7. Click **Save**.
8. Do NOT paste this key into GitHub, into chat, or into any file. If it
   ever appears in one of those, generate a new one and repeat.
9. Tell Claude "approval key added".

---

## 3. Posting posture — one decision, reply with a letter

**The boundary that holds in ALL THREE options, and cannot be traded
away by choosing one.** Whatever you pick, the AI never publishes
directly: every post still passes the release gate, which re-renders the
whole deck from the canonical store and refuses if a single fact drifted,
and every release is still bound to a signed autonomy record naming the
renderer fingerprint, the series, and the cadence. What A/B/C changes is
WHO signs and HOW OFTEN you sign — never whether a signature and a
re-verification happen. There is no option here that lets a deck reach
Instagram unverified, and any change to that boundary is a trust-invariant
change, which is yours to ratify explicitly and never an agent's to infer
from a posture choice.

Reply to Claude with **A**, **B**, or **C**:

- **A (recommended to start).** You approve every post by hand. Cadence
  1–2 per day, hard cap 2. Nothing reaches Instagram without your
  signature on that exact deck.
- **B.** You pre-approve a series (e.g. "Free tonight") for a fixed
  window; the engine posts within it at the cadence cap, and any deck
  that fails re-verification still stops for you.
- **C.** Delegated signing within the cadence cap — the standing
  authorisation signs on your behalf for a bounded window rather than you
  signing each deck. NOT unsupervised publishing: the re-render check,
  the content binding and the cadence ceiling all still run and still
  refuse. Available, but the engine should earn it on measured results
  first — this is the one that most deserves a few weeks of A behind it.

A is the default if you say nothing. Moving A → B → C later is a
one-line change, and moving back is too.

---

## 4. GitHub Actions billing — check if CI is dead

Symptom seen 2026-07-26: every workflow failing in 2–3 seconds with no
runner assigned and no logs. That is not a code failure.

1. Go to https://github.com/settings/billing
2. Look at **Actions minutes** for this month.
3. If used equals included, click **Spending limit** and either raise it
   or set a budget you're comfortable with.
4. If minutes are fine, it was a transient GitHub incident — check
   https://www.githubstatus.com and simply re-run.
5. Tell Claude what you found; nothing merges until runners come back.
