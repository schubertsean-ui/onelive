# ONE LIVE — Frictionless & Automagical Navigation (Design Spec v1)

**Status: PROPOSAL.** Two things need founder ratification: (1) the **mantra** as
an addition to the design canon (§1), and (2) this spec as the navigation/interaction
standard for `/tonight` and every surface built after it. Nothing here relaxes a
trust invariant or a gate; where a pattern brushes a trust rule (optimistic UI,
personalization, anticipation), the guardrail is written in as a hard constraint
and, where mechanizable, as an acceptance test (§13).

Author: build-agent session 2026-07-29, at founder direction ("No friction / smooth
as smooth can be should be a UX design mantra for all aspects of ONE LIVE";
"automagical … is created by no friction and accurate anticipation and assessment
and clear perception and discernment"). Grounded in the design brief v2.4, Member
Preferences v1, the Certainty Display canon, and the trust invariants; external UX
research is cited inline with source URLs in §14.

---

## 1. The mantra (proposed design-canon addition)

> ### Automagical = (No Friction) × (Accurate Anticipation)
> **Never make the user work, and never make them lose their place — and have the
> right thing already there before they reach for it.**
>
> The magic is not the absence of effort alone; it is the product *perceiving,
> discerning, assessing, and anticipating* correctly so the next right thing is
> pre-surfaced, pre-loaded, defaulted, and true. Friction removed **and** the right
> thing anticipated is what reads as *automagical*.
>
> **The trust clause (non-negotiable):** anticipation is a **lens, never a gate**.
> It may pre-surface, default, and suggest; it may never rank by money, hide
> anything real, infer where it should ask, or manufacture certainty. Magical
> *because* trustworthy — never magical by manipulation.

This extends, and does not replace, the design brief's existing emotional target —
"a friend who always knows what's on and has never once been wrong — and never
makes it about themselves" (brief §5). The mantra is the *operational* form of that
sentence.

---

## 2. Why this matters (the problem, in the founder's words)

"It's easy to get lost in tabs and windows and not remember where you were or how
to get back." That single sentence names the highest-frequency micro-friction in
any discovery product: the **context-switch tax**. Every time a user taps out to a
ticket site, a map, a venue page, or a sign-in — or even just opens a detail — they
risk losing their place, their scroll, their filters, their train of thought. A
product that eliminates that tax feels *effortless*; one that doesn't feels like
work, no matter how good its data. For ONE LIVE, whose promise is "answer 'what
should I do tonight?' in under 10 seconds," friction is not a polish item — it is
load-bearing.

---

## 3. The two pillars

Everything below hangs off two intertwined pillars. Neither alone is enough.

- **Pillar A — Frictionlessness.** Never make them lose their place; never make
  them work. (Sections 5–9: context preservation, navigation state, back-button
  discipline, external-link handling, perceived speed, frictionless auth, resume.)
- **Pillar B — Anticipation.** Perceive and discern context so the next right thing
  is already there — smart defaults, intent prefetch, resume, and the Anticipatory
  Greeting. (Section 10.)

They compound: a fast UI that also asks *less* and *pre-knows* what you want is the
whole "automagical" effect.

---

## 4. The one hard constraint that shapes everything: PWA ≠ native

**Native apps have a purpose-built tool for "link out without losing your place" —
the in-app browser tab** (`SFSafariViewController` on iOS, Chrome Custom Tabs on
Android) with a **"Done" button that returns you exactly where you were**. Reddit,
Slack, LinkedIn, and X use it. **A web PWA cannot invoke either API** — there is no
web equivalent — and worse, an outbound link from an *installed* PWA typically
**ejects the user out of the app UI into the browser** (behavior is inconsistent
across iOS/Android/versions). `<iframe>` embedding is a dead end for our targets:
Ticketmaster, maps, checkouts, and banks all send `X-Frame-Options`/CSP
`frame-ancestors` that blank the frame. (Sources: Chrome PWA navigation docs, MDN
frame-ancestors, NN/g — §14.)

**Therefore the winning PWA strategy is not to imitate the native in-app browser —
it is to make the outbound navigation unnecessary wherever possible, and honest
where it isn't:**
1. **Reduce leaves to near-zero** — resolve intent *in-context* with sheets,
   previews, and progressive disclosure (§5). Most taps should never leave at all.
2. **For the unavoidable leave** — a **labeled handoff** ("You'll finish on
   Ticketmaster, then come back here") + a **return-URL/deep-link** back into our
   scope, accepting that once on a foreign origin the *OS browser*, not us, owns the
   back button (§8).
3. **Native wrapper is the evidence-gated upgrade, not the launch bet** — an Android
   **TWA** or a Capacitor shell would restore true Custom Tabs / `SFSafariViewController`;
   it is the future unlock if data shows external-handoff return rates are hurting,
   and it ties to the open "Native mobile timing" founder decision (TODOS). We do
   **not** block launch on it, and we do **not** fake a native in-app browser (a
   spoofed chrome breaks the moment a site blocks framing, and erodes trust).

**An honesty upside we can claim:** because a PWA *cannot* inject JavaScript into
third-party pages, ONE LIVE cannot do what Meta's in-app browsers were shown to do
(observe taps, form inputs, even passwords — Krause 2022, §14). Honest handoffs also
let users keep browser autofill/passkeys — better privacy *and* better checkout
conversion than a custom webview. This is a point of principle we can state plainly.

---

## 5. Pillar A · Keep them in context (the primary toolkit)

**Principle: every outbound target — map, venue site, music, even the event detail
— is first offered as an *in-context* affordance. The outbound link is the fallback
for the committed user, never the default action.**

- **Event detail = a URL-addressable bottom sheet over the feed, not a page.** This
  is the single highest-leverage "don't lose your place" move, and it is fully
  PWA-native. The feed stays rendered behind the sheet, so there is *nothing to
  restore because the user never left*. Model it on the Google/Apple Maps
  three-state sheet (peek → half → full) and Airbnb's filter sheets. (NN/g Bottom
  Sheets; Material 3; §14.) ONE LIVE today renders detail as a full route
  (`/tonight/[id]`) — keep that route for hard loads/shares, but present it as an
  **intercepted modal sheet on soft in-feed taps** (§6).
- **Progressive disclosure / peek previews.** Resolve most curiosity with zero
  navigation: an **inline static map image** ("Directions" only on tap), an
  **inline audio preview** instead of a Spotify jump (the brief's "Hear it" already
  does this — extend the principle), venue facts *in the sheet* instead of the
  venue's site, the "How we know" explainer as a sub-sheet. (IxDF Progressive
  Disclosure; Apple HIG Context Menus.)
- **Standard vs modal sheets (Material/HIG rule):** use a **non-modal** sheet when
  the user should keep touching the feed/map behind it; a **modal** sheet (scrim,
  focus-trapped `<dialog>`) only when the task demands focus. Never bury
  always-needed controls in a sheet.

---

## 6. Pillar A · Navigation state — every view is a URL, nothing is lost

**Principle: every meaningful view — a selected event, a filter set, an open sheet
— has its own URL, so back / forward / refresh / share all reproduce it exactly.**

- **URL-addressable intercepted modal (the Instagram/`/p/<id>` model).** Next.js
  **Intercepting + Parallel Routes** give this natively: a soft in-feed tap opens
  the event in a modal slot at its own URL (`/tonight/[id]`) with the feed preserved
  behind it; a **hard load or shared link to the same URL renders the full
  standalone page**. Best of both, no state loss. (Next.js docs; §14.)
- **Filters live in the URL** (`?when=tonight&genre=live&area=east`) — shareable,
  back-restorable, server-renderable, and the same query is the deep-link and the
  redirect-back target (§9). The SPA anti-pattern to forbid: mutating view state in
  memory while the URL stays frozen at `/tonight`.
- **Scroll + filter restoration on back is mandatory.** Returning from a detail must
  land on the *exact* feed scroll offset with filters intact — never a refetch from
  the top. Losing scroll position is one of the highest-frequency frictions (NN/g
  Saving Scroll Position), and infinite feeds amplify it. Mechanisms, best-to-worst:
  **bfcache** (free, full snapshot — but a single `unload` listener or
  `Cache-Control: no-store` disqualifies it, so *protect bfcache eligibility*); the
  **Navigation API** (Baseline as of 2026) / History API with
  `history.scrollRestoration = 'manual'` for soft navigations; keep the feed layout
  from remounting in Next.js and gate restoration on content readiness.

---

## 7. Pillar A · Back-button discipline

**Principle: Back is a strict LIFO "undo my last step." It dismisses the topmost
transient layer (open sheet / modal / filter panel) *before* it leaves the page.
Never trap, never overshoot.**

- **Model every transient layer in history:** opening a sheet/modal/filter pushes a
  history entry; `popstate` closes it; when the user closes via the UI's own X or
  scrim, call `history.back()` so the stack stays consistent. Then hardware/gesture
  back "just works." (dev.to close-dialogs-by-going-back; MDN popstate.)
- **Respect platform back gestures** — Android **predictive back** (Material 3: the
  drag-preview that shows where back will land, reducing "where did that take me?")
  and iOS **edge-swipe back**. Once installed as a PWA on Android, the system back
  gesture routes through your history stack, so this must be correct or the whole app
  feels broken.
- **Sheets dismiss on Esc, scrim tap, downward swipe, and Back** — all four, and all
  reconciled with history.

---

## 8. Pillar A · External-link handling (the tabs problem, solved by intent)

**Match the pattern to the user's intent. Most "leaves" should not be leaves.**

| Intent | Examples | Pattern | Rationale |
|---|---|---|---|
| **Informational** | venue info, artist, map *preview*, "how we know" | **Stay in-app** — sheet / inline / peek. No navigation. | The leave was never needed; ~90% of taps resolve here. |
| **Transactional / terminal** | buy tickets | **Aspire to in-app/partner checkout** (DICE, Bandsintown+Ticketmaster prove in-app purchase is the gold standard). Until then: **same-tab labeled handoff** + **return-URL** to a `/tonight/…` completion route. | Checkouts block iframing and own PCI/auth; the honest handoff + return-URL is the real safety net, not Back. |
| **Directions** | turn-by-turn | inline mini-map to *see*; external maps only to *navigate*. | Don't eject someone just to see where a venue is. |
| **Save / calendar / share** | add to calendar, share | **in place** — native share sheet, generated `.ics`. | Zero-leave by construction. |

- **Default to same-tab in-scope; never gratuitously `target="_blank"` on mobile.**
  NN/g's most durable finding (held since 1999, reaffirmed 2020): new tabs
  disorient, "the old window is never visible" on mobile, and they break Back. The
  *sanctioned* exception is a reference task the user needs to keep open while acting
  elsewhere. *(ONE LIVE today opens tickets/map/venue/listen as `target="_blank"` —
  this spec revises that: informational → sheet; terminal → labeled same-tab handoff
  with return-URL.)*
- **Every true outbound link is labeled and accessible:** a visible `↗` and a
  screen-reader "external link — opens [Ticketmaster]" announcement (WCAG-adjacent;
  an unannounced context change is a defect — CMS Design System "third-party external
  link"; Brickfield). Reserve the explicit "you are leaving" interstitial for
  transactional/trust-sensitive jumps; casual links just get the `↗` label.
- **Do not over-warn** — an interstitial on every link trains users to blow past it.

---

## 9. Pillar A · Perceived speed + frictionless auth

### 9.1 Perceived performance (the research baseline)
Design against **NN/g 0.1 / 1 / 10 s** and the **Doherty threshold (~400 ms)**:
give *some* acknowledgment (press state / skeleton / optimistic update) within
~100–200 ms even when the backend is slower. Perceived speed beats raw speed by
*separating acknowledgment (instant) from completion (async)*.

- **Skeleton screens, not spinners**, for the card feed (Facebook/YouTube/LinkedIn).
  Rules: <100 ms no indicator; 100–400 ms small inline spinner; 400 ms–3 s skeleton;
  >3 s skeleton + progress. **Delay the skeleton ~200 ms to avoid the "blink," and
  match final layout exactly (protects the CLS budget).** Next.js `loading.tsx` /
  Suspense give this nearly for free.
- **Optimistic UI for the user's own reversible actions** (save / RSVP): apply
  instantly, reconcile async, roll back with a quiet toast on failure (Instagram
  likes; Linear). **Trust guardrail (hard):** optimistic UI must **never** imply an
  event is `confirmed`/verified or that a *claim* is approved — those reflect true
  server/gate state only. Optimism is confined to the user's own reversible actions
  (consistent with "AI never publishes" and the 4-state model).
- **Prefetch on intent:** Next.js `<Link>` prefetch for in-viewport cards; prefetch
  detail data on hover (desktop) / viewport (mobile); Speculation Rules API as
  progressive enhancement. Respect `Save-Data`/`prefers-reduced-data`.
- **Progressive-enhancement View Transitions** (Baseline 2025) for feed↔detail —
  a card that morphs into its detail (and back on close) tells the eye where the
  view came from and implicitly promises Back reverses it. Feature-detect
  (`if (document.startViewTransition)`), honor `prefers-reduced-motion` (WCAG 2.2),
  keep it ~200–300 ms against the LCP ≤ 2.5 s budget.

### 9.2 Frictionless auth / registration / claim
- **Defer auth to the last responsible moment (lazy registration).** Browse, filter,
  open detail, even tap through to tickets with **no account**; raise auth only when
  the action *needs* identity (save, RSVP, claim, tastemaker post). The "$300M
  button" (guest path → +45% purchases) and Baymard (forced account creation causes
  ~24–26% of checkout abandonment) are the canonical proof; NN/g: users are rarely
  "more annoyed" than at a login wall. This is already a ONE LIVE principle ("no
  account, no login" — brief) — this spec hardens it: **never gate browse/filter/
  detail; gate only write/claim actions.**
- **Anonymous-first, upgrade-in-place.** When a user first does something worth
  persisting (save an event), create an anon identity and **link it to the real
  account on sign-in** so nothing is lost — registration becomes a no-loss upgrade
  ("keep your saved events"). **RLS guardrail:** the anon id is a first-class
  principal under Supabase RLS, still fail-closed — never an escape hatch.
- **Passwordless stack:** **magic link + email OTP** as the mobile/new-user path,
  **passkeys via Conditional UI** (autofill) as the quiet returning-user upgrade,
  **Google One Tap** optional — never the only path. Plain-language labels ("we'll
  email you a secure link"), never "WebAuthn." Fits an events app's infrequent,
  multi-device use. (Clerk, our auth vendor, supports these.)
- **Redirect-back to the exact intended action** — capture where they were + what
  they intended, and after auth drop them back there with the action pre-loaded,
  never a generic home. **Mobile gotcha:** magic-link auth completes in a new
  tab/email client, so encode the return target *inside the link's `state`* (and/or
  prefer same-tab OTP) so the SPA restores in place. **Security:** validate the
  return target against an allowlist of our own paths (no open redirects).

---

## 10. Pillar B · Anticipation (what makes it *automagical*)

Friction removal alone gets to "smooth." Anticipation gets to "magic." Anticipation
is where "accurate assessment and clear perception and discernment" become design
requirements, not vibes.

- **Resume where you left off.** Bring returning users straight back to context —
  feed scroll + filters (URL/session), the event they were viewing, an in-progress
  claim/RSVP draft (localStorage/IndexedDB → "Resume your claim"), and, for
  signed-in users, cross-device "last viewed" (a genuine *reason to register*). A
  quiet "welcome back — still deciding? here's what you were looking at" beats a cold
  start (Netflix Continue Watching; Kindle furthest page; Spotify position). Offer
  resume as a *cue, not a forced jump* (don't dump users into a flow they've
  mentally abandoned).
- **Smart defaults / reduce decision fatigue.** Default to **tonight + near me**;
  reveal advanced filters progressively; never force a choice (auth method, filters)
  before the user has a reason to care. Fewer, smarter choices per step = effortless
  (Hick's Law-adjacent).
- **The Anticipatory Greeting (the "returning-friend prompt").** The surface where
  frictionlessness and anticipation meet — the greeting *is* the resume affordance,
  the personalization, and the value-surfacing, in one low-effort line. Reference
  micro-copy (founder-supplied):
  > `hey joe, looking for more wine experiences or something else?`
  > `hi amy, want to see more on women's groups or something else?`
  > `hi, 7 R&B shows in town this next week — check it?`

  **Three hard guardrails (what keeps it magical *and* trustworthy):**
  1. **"…or something else?" is mandatory, not decorative.** Every anticipatory
     prompt carries a one-tap escape and never narrows what is actually shown —
     anticipation is a *lens, never a gate*. This is what keeps it from becoming a
     filter bubble or a trap.
  2. **Numbers must be true.** "7 R&B shows" must be a *verified, resolved* count
     (`confirmed`-tier; `disputed` shown as disputed, never counted). Anticipation
     inherits the trust layer — a greeting that overstates is worse than none. This
     is where "accurate assessment / clear discernment" is a hard requirement.
  3. **Consent-gated, and graceful for strangers.** Knowing "Joe likes wine" comes
     from on-device defaults / declared preferences (Member Preferences P1/P2),
     never silent inference (never "emotion recognition" — the emotion layer's
     declared-preference rule). An anonymous first-time visitor still gets an
     anticipatory-but-impersonal version ("7 R&B shows in town this week — check
     it?") so the no-account path stays first-class. **Perceive and discern, but
     ask where you should ask.**

---

## 11. Trust guardrails (consolidated — the invariant intersections)

Frictionlessness and anticipation must never buy smoothness with trust. The binding
constraints, in one place:

1. **Anticipation is a lens, never a gate** — it pre-surfaces and defaults; it never
   ranks by money, hides anything real, or reorders discovery. (No-pay-to-rank;
   disputed-shown-never-hidden.)
2. **Optimistic UI only for the user's own reversible actions** — never to imply a
   verified/`confirmed` event or an approved claim. (AI-never-publishes; 4-state
   model.)
3. **Personalization is declared, never inferred** where inference would be
   surveillance — consent-gated, on-device-first (Member Preferences; emotion-layer
   declared-preference rule; TDPSA "precise geolocation is sensitive").
4. **No dark patterns.** Every anticipatory/greeting/return mechanism must pass the
   design brief's "reflection test" (white-hat only) — no manufactured FOMO, no
   coercive prompts. The mandatory "…or something else?" out is the structural form
   of this.
5. **Anon principals are fail-closed under RLS** — anonymous-first identity is never
   an authorization escape hatch.
6. **Honesty over polish** — no faked native in-app browser, no interstitial theater,
   no "smooth" that misleads (e.g., never render a read error as "no such event").

---

## 12. What this means for ONE LIVE today (delta from current build)

- **Keep** the `/tonight/[id]` route (good for hard loads + shares) and the "Hear
  it" inline preview and the `← Tonight` back link — all already aligned.
- **Add** the intercepted-modal presentation so in-feed taps open detail as a sheet
  over the preserved feed (§6).
- **Add** scroll + filter restoration on back and filters-in-URL (§6).
- **Revise** external-link handling: informational links (venue, map preview, "how
  we know") move in-app; only terminal ticket/directions leave, as a labeled
  same-tab handoff with a return-URL and `↗`/screen-reader labeling (§8). Replaces
  the current blanket `target="_blank"`.
- **Add** history-modeled sheets so Back closes the sheet before leaving (§7).
- **Add** skeletons, optimistic save/RSVP (with the trust caveat), prefetch-on-intent,
  and feature-detected View Transitions (§9.1).
- **Build** the auth/claim flows lazy + anon-first + passwordless + redirect-back
  from the start (§9.2) — this lands with the Clerk allowlist/claim work (SPRINT
  Step 8/9).
- **Design in** resume + smart defaults + the Anticipatory Greeting as the surfaces
  mature (§10), consent-gated per Member Preferences phasing.

---

## 13. Acceptance tests (mechanical where possible — "physics, not policy")

Mirroring ONE LIVE's enforce-by-mechanism culture. Legend: **[unit]** automatable
test · **[lint]** static check · **[a11y]** axe/keyboard · **[perf]** Lighthouse/CWV
· **[qa]** scripted manual.

1. **[lint]** No internal navigation uses `target="_blank"`; every `target="_blank"`
   is on an allowlisted *external* origin and carries `rel="noopener noreferrer"`.
2. **[unit/qa]** Back from any event detail restores the feed's exact scroll offset
   **and** the active filters; the feed is not refetched-from-top.
3. **[qa]** bfcache eligibility holds on feed pages (no `unload` listener, no
   `Cache-Control: no-store`) — verified in DevTools → Back/forward cache.
4. **[unit/qa]** Opening a sheet/modal/filter pushes a history entry; hardware/gesture
   **Back closes the topmost layer before leaving the page**; UI-close and Back leave
   an identical, consistent history state.
5. **[a11y]** Every modal sheet traps focus, returns focus to its trigger on close,
   and dismisses on Esc / scrim / swipe / Back.
6. **[lint/qa]** Every meaningful view is URL-addressable: a shared/refreshed
   `/tonight/[id]` renders standalone; `?when=…&genre=…` reproduces the filtered feed.
7. **[a11y]** Every external link exposes a visible `↗` and a screen-reader
   "external link, opens [destination]" label; transactional jumps show a labeled
   handoff.
8. **[qa]** A completed external ticket handoff returns the user to a `/tonight/…`
   in-scope route (return-URL), not a dead browser tab.
9. **[perf]** Feed uses skeletons (not spinners) with ≥200 ms delay-to-avoid-blink
   and zero CLS from placeholders; LCP ≤ 2.5 s (brief budget) holds.
10. **[unit]** Optimistic UI is applied only to the user's own reversible actions;
    a test asserts confidence state / claim-approval render from server truth and are
    never set optimistically.
11. **[qa]** No account is required to browse, filter, or open detail; auth is
    requested only on save/RSVP/claim/post, and after auth the user lands on the exact
    intended action (return target validated against an internal allowlist).
12. **[unit]** Anonymous-first identity links to the account on sign-in with nothing
    lost; anon rows are fail-closed under RLS (a policy test).
13. **[unit]** Every Anticipatory Greeting carries a "…or something else?" escape and
    does not filter the underlying feed; any count it states is derived from
    `confirmed`/resolved rows (a test asserts the count query excludes
    `disputed`/`unverified`).
14. **[a11y/qa]** `prefers-reduced-motion` disables View Transitions and non-essential
    motion; the app is fully operable with transitions unsupported (feature-detected).
15. **[qa]** Every interactive control has a voice-phrase mapping (ties to the
    existing Voice-Navigation founder requirement) — anticipation and voice share the
    same accessibility grammar.

---

## 14. Sources (curated; full set in the research threads)

**Authorities:** NN/g — [New Windows & Tabs](https://www.nngroup.com/articles/new-browser-windows-and-tabs/),
[Bottom Sheets](https://www.nngroup.com/articles/bottom-sheet/),
[Saving Scroll Position](https://www.nngroup.com/articles/saving-scroll-position/),
[Login Walls](https://www.nngroup.com/articles/login-walls/),
[Response Times](https://www.nngroup.com/articles/response-times-3-important-limits/) ·
Material 3 — [Bottom sheets](https://m3.material.io/components/bottom-sheets/guidelines),
[Predictive back](https://developer.android.com/design/ui/mobile/guides/patterns/predictive-back),
[Material motion](https://m3.material.io/blog/android-material-motion) ·
Apple HIG — [Modality/sheets](https://developer.apple.com/design/human-interface-guidelines/modality),
[Context menus](https://developer.apple.com/design/human-interface-guidelines/components/menus-and-actions/context-menus/) ·
Laws of UX — [Doherty Threshold](https://lawsofux.com/doherty-threshold/),
[Peak-End Rule](https://lawsofux.com/peak-end-rule/).

**Web platform:** [bfcache](https://web.dev/articles/bfcache) ·
[Navigation API](https://web.dev/blog/baseline-navigation-api) ·
[View Transitions 2025](https://developer.chrome.com/blog/view-transitions-in-2025) ·
[PWA navigation management](https://developer.chrome.com/docs/capabilities/pwa-navigation-management) ·
[Chrome Custom Tabs](https://developer.chrome.com/docs/android/custom-tabs) ·
[MDN frame-ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors) ·
[Passkey form autofill](https://web.dev/articles/passkey-form-autofill) ·
Next.js [Intercepting routes](https://nextjs.org/docs/app/api-reference/file-conventions/intercepting-routes).

**Handoff & auth:** [CMS "third-party external link"](https://design.cms.gov/components/third-party-external-link/) ·
[Auth0 redirect-after-login](https://auth0.com/docs/login/redirect-users-after-login) ·
[Bandsintown+Ticketmaster in-app purchase](https://musically.com/2016/03/24/bandsintown-and-ticketmaster-debut-in-app-ticket-purchases/) ·
in-app-browser privacy — [Felix Krause](https://krausefx.com/blog/ios-privacy-instagram-and-facebook-can-track-anything-you-do-on-any-website-in-their-in-app-browser).

**Perceived speed:** [Skeleton screens](https://blog.logrocket.com/ux-design/skeleton-loading-screen-design/) ·
[Optimistic UI / Doherty](https://blog.logrocket.com/ux-design/designing-instant-feedback-doherty-threshold/) ·
[Prerender on hover](https://css-tricks.com/prerender-on-hover/).

**ONE LIVE canon referenced:** `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md`
(trust display, WCAG 2.2 AA, LCP ≤ 2.5 s, "a friend who always knows") ·
`docs/strategy/ONE_LIVE_MEMBER_PREFERENCES_v1.md` ("personalization is a LENS, never
a GATE") · `docs/strategy/ONE_LIVE_CERTAINTY_DISPLAY_v1.md` (4-state) · `CLAUDE.md`
(trust invariants) · current `web/app/(public)/tonight/`.

---

## 15. Open questions for the founder (decide one-by-one)

1. **Ratify the mantra** (§1) as a design-canon addition (a one-line entry in the
   brief's principles)? — the only thing that makes "automagical" binding rather than
   aspirational.
2. **Ticketing:** pursue an **in-app/partner checkout** (DICE/Bandsintown model) with
   Ticketmaster/SeatGeek where volume justifies, vs. the labeled-handoff-only path?
   (Partner-API integration = new scope; founder-crucial where it touches money/new
   services.)
3. **Native wrapper trigger:** what external-handoff return-rate (once measured) would
   justify shipping a TWA/Capacitor shell for true Custom Tabs? (Ties to the open
   "Native mobile timing" decision.)
4. **Anticipatory Greeting go-live:** confirm it launches *after* Member-Preferences
   consent surfaces exist, and that the anonymous (impersonal) variant is acceptable
   for first-time visitors.
