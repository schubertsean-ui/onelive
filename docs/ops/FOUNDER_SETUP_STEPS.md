# Founder setup — explicit steps, not summaries

**Standing rule (founder directive, 2026-07-26, verbatim: "Never make me
ask again for Explicit 'how to' step by step").** Any time the founder is
asked to do something, the ask ships as click-by-click steps: the exact
URL, the exact button text, the exact field name, and what to paste. A
bullet naming a task without its steps is a defect, not a summary.

SCOPE, corrected 2026-07-26 after this sentence was found contradicting
CLAUDE.md rule 7: this rule governs ASKS — anything the founder must DO. On
those, step-detail supersedes brevity. It does NOT license long REPORTS. Rule
7 governs those and is explicit that length is a defect; an ask written in
full and a report kept under thirty seconds are not in tension, because most
work should produce a report and no ask at all.

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
5. Instagram now offers to connect a Facebook Page.
   - **If you already have a Page:** tap **Connect an existing Page**,
     tap your Page in the list, then tap **Done**.
   - **If you have no Page**, make one first:
     - i. Go to https://www.facebook.com/pages/create
     - ii. In **Page name** type exactly: `OneLive`
     - iii. In **Category** type `Entertainment Website` and pick it from
       the dropdown that appears.
     - iv. Leave **Bio** empty. Click **Create Page**.
     - v. Skip every "add a photo / invite friends" prompt — click
       **Skip** or **Next** until you land on the Page itself.
     - vi. Return to the Instagram screen and tap **Connect an existing
       Page**, pick `OneLive`, tap **Done**.
   The Page holds the API permission; nobody has to visit it.

### 1b. Create the Meta app (10 min)

1. Go to https://developers.facebook.com/apps
2. Click **Create app**.
3. If asked "What do you want your app to do?", choose **Other**.
4. For app type choose **Business**. Click **Next**.
5. In **App name** type exactly: `OneLive Posting`
   In **App contact email** enter your own email address.
   Leave **Business portfolio** as whatever is pre-selected.
   Click **Create app**, and re-enter your Facebook password if prompted.
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
5. Click **Generate Access Token**. A Facebook popup opens. Work through
   it in this order, and do not click "Opt in to all" shortcuts:
   - a. Click **Continue as {your name}**.
   - b. On the Pages screen, tick ONLY the Page from step 1a. Click
     **Continue**.
   - c. On the Instagram screen, tick ONLY the Instagram account from
     step 1a. Click **Continue**.
   - d. The permissions screen lists the five scopes as toggles. Confirm
     every one is **On** — if `instagram_content_publish` is off, the
     posting API will fail later with a permissions error that looks
     unrelated. Click **Save** (some versions say **Done**).
   - e. Back on the confirmation screen, click **Got it** / **OK**.
6. Copy the token that appears in the **Access Token** box. It is
   short-lived — step 1d fixes that.
7. Sanity check before moving on: the box under the token should list all
   five scopes. If any is missing, repeat 4–6; a token with partial
   scopes fails silently at posting time, not now.

### 1d. Make the token long-lived (5 min)

1. Still in Graph API Explorer, click the **ⓘ** icon next to the token.
2. Click **Open in Access Token Tool**.
3. Click **Extend Access Token** at the bottom.
4. Copy the new token. **This is your `META_ACCESS_TOKEN`.** It lasts
   about 60 days — set a calendar reminder for 50 days from today.

**Handle this token like a password — it can post as you.** Unlike the two
IDs in step 1e, this is a bearer credential: anyone holding it can publish
to your Instagram account without any further check. So:
   - a. Do NOT paste it into a chat with Claude, into a GitHub issue or PR,
     into a commit, or into any file in the repo. The only place it goes is
     the GitHub secret box in step 1f.
   - b. Do NOT email it or send it over Slack/Messages to anyone, including
     to yourself as a note.
   - c. If it lands anywhere on that list even briefly, treat it as burned:
     go to https://developers.facebook.com/apps → `OneLive Posting` →
     **Settings** → **Advanced** → **Invalidate all access tokens**, then
     repeat steps 1c and 1d to mint a fresh one.
   - d. Between copying it in step 4 and pasting it in step 1f, keep it on
     the clipboard only. If you must park it somewhere, use your password
     manager, never a notes app or a text file.

**When it expires (or if posting starts failing):** the symptom is a
posting error mentioning an invalid or expired OAuth token. Recovery:
   - a. Repeat steps 1c and 1d exactly to mint a fresh long-lived token.
   - b. Go to https://github.com/schubertsean-ui/onelive/settings/secrets/actions
   - c. Click the pencil icon next to `META_ACCESS_TOKEN`.
   - d. Paste the new token and click **Update secret**.
   - e. The two IDs do NOT change — leave `META_FB_PAGE_ID` and
     `META_IG_USER_ID` alone.
   - f. Tell Claude "token rotated".

### 1e. Find the two IDs (5 min)

*Unlike the token, these two IDs are NOT secrets* — they are public
account identifiers, and holding one grants nobody anything. You can paste
them into chat or a file freely. Only `META_ACCESS_TOKEN` needs the
handling rules in step 1d.

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
6. Confirm all three appear in the list. GitHub masks secrets after
   saving — you will not be able to read `META_ACCESS_TOKEN` back, which is
   correct and expected. If you need it again, re-mint it (steps 1c–1d).
7. **Now clear the token from your clipboard** — copy any harmless text to
   overwrite it. If you parked it anywhere in step 1d, delete that copy now.
8. Tell Claude "Meta credentials added" — send that phrase and nothing
   else. Do NOT paste the token or any part of it into the chat as
   confirmation; Claude never needs to see it and cannot use it. That
   phrase fires R-026 and unlocks the posting client.

---

## 2. `ONELIVE_APPROVAL_KEY` — signs your carousel approvals

This is the secret that makes an approval provably yours. Without it, no
post can be signed, so nothing can publish even with Meta connected.

1. Generate a random key. On a Mac, open Terminal and run:
   ```
   openssl rand -base64 48
   ```
   Copy the whole output line.

   **No terminal? Use another OFFLINE generator — never a website.** This
   key signs publish approvals, so it must never be created inside a page
   served by someone else: you cannot verify from here what that page does
   with it, and a signing key that leaves your machine can forge approvals.
   Pick whichever applies:
   - a. **Windows** — press Start, type `powershell`, open it, and paste
     this exactly (one line):
     ```
     [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
     ```
     Press Enter and copy the whole output line.
     Do NOT substitute `Get-Random` here even though it looks equivalent —
     it is a general-purpose random number generator, not a cryptographic
     one, and a signing key generated from it is guessable in ways that do
     not show up until someone forges an approval.
   - b. **Linux** — open Terminal and run the same `openssl rand -base64 48`
     as above.
   - c. **A password manager you already have installed** (1Password,
     Bitwarden, Apple Passwords) — use its BUILT-IN generator in the app,
     not its website: create a new item, set length **64**, Numbers and
     Symbols ON, and save the item. Generating it there also stores it
     safely in one step.
   - d. **iPhone, nothing else to hand** — in Notes you cannot generate one
     safely; use Apple Passwords: add a new password entry for `onelive`
     and let it generate, then reveal and copy it.
   Do not shorten below 64 characters, and do not use a website generator
   even if it claims to run locally — that claim is not checkable from here.

**Handle this key like the Meta token — it signs publish approvals.** Same
boundary, stated here so this section stands on its own:
   - a. Do NOT paste it into a chat with Claude, a GitHub issue or PR, a
     commit, or any file in the repo. The only place it goes is the Vercel
     value box in step 5.
   - b. Do NOT email it or send it over Slack/Messages to anyone, including
     to yourself as a note.
   - c. Keep it on the clipboard only between generating and pasting. If you
     must park it, use your password manager — never a notes app or a text
     file.
2. Go to https://vercel.com/sss-projects-e4775771/onelive/settings/environment-variables
3. Click **Add New** (or **Create new**).
4. Key: `ONELIVE_APPROVAL_KEY`
5. Value: paste the generated key.
6. Environments: tick **Production ONLY**. Untick Preview and
   Development — a signing key in Preview is a signing key on a public
   URL.
7. Click **Save**.
8. **Now clear it from your clipboard** — copy any harmless text to
   overwrite it. If you parked it in a password manager that is fine; if it
   went anywhere else in step 1, delete that copy now. Vercel masks the
   value after saving, so you will not be able to read it back — that is
   correct and expected.
9. **If it ever leaks** — into GitHub, chat, an email, a Slack message, a
   commit, or any file — rotate it, do not just delete the copy:
   - a. Generate a new key (step 1).
   - b. Return to
     https://vercel.com/sss-projects-e4775771/onelive/settings/environment-variables
   - c. Click the **⋯** menu next to `ONELIVE_APPROVAL_KEY` → **Edit**.
   - d. Paste the new value, keep **Production ONLY** ticked, click **Save**.
   - e. Redeploy so the new value takes effect, then tell Claude
     "approval key rotated". Approvals signed with the old key stop
     verifying, which is the point.
10. Tell Claude "approval key added" — that phrase and nothing else. Do NOT
    paste the key or any part of it into the chat as confirmation; Claude
    never needs to see it and cannot use it.

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
2. In the left sidebar click **Plans and usage**.
3. Find the **Actions** row. Read it as `used / included` minutes.

**If used has reached included** — raise the limit:
4. In the left sidebar click **Spending limit**.
5. Find the **Actions and Packages** section.
6. Select the radio button **Limited spending** (not *Unlimited* — an
   unlimited setting removes your ceiling entirely).
7. In the field labelled **Spending limit (USD)** type a number you are
   comfortable with. `20` is roughly 2,000 extra Linux minutes, far more
   than a normal week here.
8. Click **Update limit**.
9. Give it about a minute, then tell Claude "spending limit raised".

**If minutes are NOT exhausted** — it was a GitHub incident:
10. Check https://www.githubstatus.com for a green Actions row.
11. Go to https://github.com/schubertsean-ui/onelive/actions
12. Click the topmost failed run in the list.
13. Top right, click **Re-run jobs** → **Re-run all jobs**.
14. Tell Claude "re-ran, minutes are fine".

Either way, nothing merges until runners come back — say which branch you
took and Claude picks it up from there.
