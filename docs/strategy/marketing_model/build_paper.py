# -*- coding: utf-8 -*-
from weasyprint import HTML

# tier keys: SO=solo, S=small, M=medium, L=large, J=jumbo
CATS = [
 # ---- VENUES & PLACES ----
 dict(g="Venues & Places", n="1 · Live music venues & clubs (independent, ≤1,500 cap)", src="NIVA",
  snap="The heart of the supply side. 64% were NOT profitable in 2024 (NIVA State of Live); sector still contributed $86.2B to GDP. Squeezed by rent/insurance/staffing inflation, declining alcohol sales, ticketing-giant practices, and 'competition from the couch.'",
  ch=["Margins: costs up (rent, insurance, artist guarantees), bar revenue per head down", "Half-full weeknights; discovery failure = direct spoilage of a perishable product", "Owner/GM attention exhausted by operations; marketing is the sacrificed hour", "Ticketing/resale platforms capture fan data and fees"],
  gr=["Fill soft nights (Sun–Wed) and grow per-head spend", "Own the fan relationship (list, regulars) instead of renting it from platforms", "Diversify programming (comedy, trivia, private events) without losing identity"],
  val=["Which nights hurt, and what have you tried?", "Where do new faces actually come from today?", "Who does your promotion this week — and what does it cost you in hours?", "What would you do with 20 more covers on a Tuesday?"],
  recs={"S":"Lead with the Mirror + soft-night pain; agent = free presence + midweek promotion kits; door codes prove lift.",
        "M":"Multi-room/series coherence + one feed for all rooms; digest for the GM; pipe consistency for every property.",
        "L":"API/feed integration with their existing ticketing + agent-traffic log as the exec-friendly artifact."},
  angle="'64% of rooms like yours lost money last year. The nights you don't fill are the whole margin. Here's what AI says about you tonight — and the free fix.'"),
 dict(g="Venues & Places", n="2 · Bars, pubs & cocktail lounges with programming", src="NIQ/nightlife",
  snap="Neighborhood bars, pubs, and cocktail rooms running trivia, karaoke, DJs, and live music as the traffic answer to declining default drinking. Late-night hospitality contracted ~29% in six years (UK data; US directionally similar) — programming is the strategy, but the chalkboard is the marketing plan.",
  ch=["Events exist only on a chalkboard and an IG story; invisible to search/AI", "No one owns marketing; the 'events person' is a bartender with Canva", "Declining drinking = must sell the NIGHT, not the drink", "Late-night cost structure with earlier-going customers"],
  gr=["Make recurring nights reliable traffic engines", "Capture regulars into an owned list", "Prove which events move the register"],
  val=["Which recurring night pays for itself, and how do you know?", "Where would someone find your Thursday lineup right now?", "Who decided your last event, and how was it promoted?"],
  recs={"S":"One-URL setup; recurring-series function (describe trivia once); QR list capture at the bar.",
        "M":"(Bar groups) multi-location consistency + per-location digests; kits for flagship nights."},
  angle="'People drink less and choose occasions more. Your Tuesday trivia IS the strategy — but tonight it is invisible to everyone who asks their phone.'"),
 dict(g="Venues & Places", n="3 · Breweries, wineries, distilleries & tasting rooms", src="BA/SVB",
  snap="Production-plus-hospitality businesses with a THREE-SIDED revenue model: the visit (taproom/tasting room), the product (bottles, cases, retail, DTC club shipments), and the experience (ticketed tastings, tours, pairing dinners, classes and education). The traffic tide is out on all three: craft-beer closings outpaced openings for the second straight year (434 vs 268 in 2025 — the Brewers Association calls it 'the fight for occasions'); tasting-room visits fell across wine regions (Napa −18%, Sonoma −8%, Paso Robles −12%) while the winery count grew 7,500 → 11,000 since 2019; club growth stalled to ~2% nationally — and ~90% of club signups happen IN the tasting room, so lost visits compound directly into lost recurring revenue.",
  ch=["Occasions, not visitors: fewer default trips means every visit must be MANUFACTURED — releases, tours, live music, markets, family days, ticketed tastings", "The club/membership engine (their LTV core) starves when door traffic falls: ~90% of signups happen on premises", "Education and experience products (classes, pairing dinners, blending workshops) are high-margin and list-building — but are marketed worst of all: buried on a page nobody visits", "Destination economics: drive-to businesses where a wasted trip (wrong hours, no event, sold-out tasting) is unforgiving", "Production + hospitality + retail + marketing shared across the same two or three heads"],
  gr=["Rebuild visit traffic through event occasions and bookable experiences", "Grow club and membership signups (the recurring-revenue engine)", "Sell more experience inventory: tastings, tours, classes, dinners — ticketed, higher-margin, and each one a captive list-building audience", "Move product: release-day velocity, retail attach on visits, DTC between visits", "Reach daytime, family, and tourist segments beyond the enthusiast core"],
  val=["What share of revenue is on-premise vs product/DTC vs experiences (tastings, classes, dinners)?", "How does anyone learn a release, class, or event is happening?", "What is a club member worth, and where do signups actually happen?", "Do your tastings and classes sell out — and who fills the empty seats?"],
  recs={"S":"Release-and-event kits (drop days are their biggest moments); TICKETED-experience listings (tastings/tours/classes as first-class bookable events with their existing ticketing linked); hours/seasonal accuracy across the maps pipes; club-signup link on every listing.",
        "M":"Multi-location (taproom + satellite) consistency; experience-calendar sync (education series, dinners) alongside events; series brands (run club, night market); daytime/family tagging.",
        "L":"(Regional brands with hospitality arms) integration with reservation/club/ticketing platforms; per-location digests; accuracy reporting across the portfolio."},
  angle="'You sell three things — the visit, the bottle, and the experience — and all three start with someone finding out something is happening. Every release, tasting, class, and market day findable everywhere people ask, free; every visit a chance at a club signup.'"),
 dict(g="Venues & Places", n="4 · Restaurants & cafés with events (patio stages, jazz brunch, supper clubs)", src="NRA 2026",
  snap="$1.55T industry, cautiously optimistic, but 9-in-10 operators cite food/labor/insurance/energy/swipe-fee pressure and staffing is the #1 challenge (33% by mid-2026). Events are a traffic lever they run with zero marketing muscle.",
  ch=["Uneven traffic; stretched lower/middle-income guests", "Labor churn makes any marketing 'system' impossible — the person leaves", "Events are an afterthought run off a laminated flyer"],
  gr=["Weeknight and shoulder-hour traffic", "Loyalty/direct lists to reduce third-party platform dependence", "Differentiation in an oversupplied dining market"],
  val=["Does live programming measurably lift covers — do you know?", "What's your slowest profitable-if-full window?", "Who quits next and what breaks when they do?"],
  recs={"S":"Agent survives staff churn (system owns the loop, not a person); calendar sync from whatever they already use.",
        "M":"Group-level feed + per-location kits; measurement in covers language, not impressions."},
  angle="'Your marketing system shouldn't quit when your server does. Free, three taps, and your Thursday jazz shows up when someone asks AI where to eat tonight.'"),
 dict(g="Venues & Places", n="5 · Theaters & performing arts centers", src="Theater surveys",
  snap="Audiences ~34% below 2019, subscribers down ~44%; audiences aging (and 84% white — a named diversification goal). Costs inflated, philanthropy shifting. Single-ticket, last-minute buying replaced subscriptions — exactly the discovery pattern OneLive serves.",
  ch=["Subscription model decay → every show must be sold individually", "Aging core audience; younger/diverse audiences don't arrive via brochures", "Marketing staff (if any) consumed by season mechanics"],
  gr=["Reach under-45 and diverse audiences where they decide (phones, night-of)", "Convert single-ticket strangers into repeat attenders", "Digital/streaming experiments that proved out in the data"],
  val=["What share of your house is bought within 72 hours of curtain?", "What's your cost to acquire a NEW (not returning) attender?", "Where does a 30-year-old find you tonight?"],
  recs={"M":"Season-to-feed sync (one import, every performance current); accessibility of listings to AI = the young-audience channel.",
        "L":"Integrate with Tessitura/Spektrix-class systems via ICS/feeds; the E-standard as a board-presentable accuracy report."},
  angle="'Your next subscriber has never bought a subscription. They decide Thursday for Friday, by asking. Be the answer — free.'"),
 dict(g="Venues & Places", n="6 · Comedy clubs & rooms", src="est. + NIVA-adjacent",
  snap="The boom category: post-2021 comedy demand surged (specials halo, podcast audiences), rooms multiplying — including comedy nights inside music venues and bars. Data thinner than music (validate in conversations); economics mirror small venues with better bar margins.",
  ch=["Discovery skew: fans follow COMICS, not rooms — the club must ride names it books", "Weeknight open-mic-to-showcase pipeline needs constant local promotion", "Same cost inflation as music rooms"],
  gr=["Build room-brand loyalty independent of headliners", "Sell out weekends earlier; fill industry nights", "Capture the touring-comic bump into a local list"],
  val=["Does a headliner's audience ever come back for the room?", "How do locals find your Tuesday showcase?", "What % of seats sell night-of?"],
  recs={"S":"Lineup-sync (nightly changes flow automatically); comic-tagging so the artist edition cross-promotes the room.",
        "M":"Multi-show-per-night handling; kits per headliner announcement."},
  angle="'Fans follow the comic. The room that's always accurate everywhere is the room the comic's fans find. Free.'"),
 dict(g="Venues & Places", n="7 · Nightlife: dance clubs & DJ rooms", src="NIQ/NPR nightlife",
  snap="The hardest-hit venue class: late-night closures at ~6/month (UK), 2025 a 'rough year' for US clubs (NPR) — high rents, less drinking, earlier nights. Survivors win on event-brand strength and direct community.",
  ch=["Structural demand shift (earlier, less alcohol) — must sell the NIGHT as an event", "Promoter-dependent calendars; the club often doesn't control its own listings", "Younger audience lives on IG/TikTok; nothing machine-readable exists anywhere"],
  gr=["Event-brand series that sell regardless of lineup", "Direct lists/SMS to bypass algorithm decay", "Earlier/alternative formats (day parties) that need NEW audiences"],
  val=["Who actually controls your event data — you or your promoters?", "What's your ratio of walk-up vs presale?", "Which series would you bet the room on?"],
  recs={"S":"Promoter-and-room dual claim (scoped authority — both maintain, gate reconciles); SMS-list capture kits.",
        "M":"Series-brand pages + day-party launch kits aimed at new segments."},
  angle="'The clubs surviving aren't the loudest — they're the ones their city can actually find. Your residencies, right, everywhere, free.'"),
 dict(g="Venues & Places", n="8 · Galleries & independent art spaces", src="art-market adjacent",
  snap="Squeezed by art-market softness and rent; openings are their 'events' but are promoted to an existing email list and nobody else. Openings/closings/artist talks are classic weak-signal events — rarely structured anywhere. (Thin public data; validate.)",
  ch=["Shows change monthly; websites don't", "Audience = collectors + scene; no growth channel to culturally-curious newcomers", "One person does everything, including the hanging"],
  gr=["New foot traffic beyond the list (younger buyers)", "Position openings as nights out, not trade events", "Artist-gallery cross-promotion"],
  val=["Who came to your last opening that you didn't already know?", "How does a new-to-town art lover find you?", "What would 50 strangers at an opening be worth?"],
  recs={"SO":"(Artist-run spaces) person+place dual edition; opening-night kits.",
        "S":"Exhibition-cycle sync (one entry per show → opening + run + closing events auto-published)."},
  angle="'Every opening is a free party most of the city never hears about. Fix that in three taps.'"),
 dict(g="Venues & Places", n="9 · Museums & cultural institutions", src="AAM/NPR",
  snap="Recovery reversing: 55% below 2019 attendance; a third lost federal grants in 2025 and 67% couldn't replace them — programming cut exactly when they need earned revenue and local audiences most. 'Think local' is now the stated strategy (Art Newspaper).",
  ch=["Funding shock → smaller marketing teams, bigger earned-revenue targets", "Programming (lates, concerts, family days) is the growth engine but is marketed like exhibitions", "Institutional web presence ≠ event discoverability"],
  gr=["LOCAL repeat visitation (the tourist model broke)", "After-hours/experience programming for under-40s", "Membership growth from event attendees"],
  val=["What share of visitors are locals vs tourists now?", "How do you market a Friday late — and to whom?", "What did the grant cuts change about this year's plan?"],
  recs={"M":"Program-calendar sync (their CMS → feed); membership-capture links on every event.",
        "L":"Institution-grade: departmental calendars unified; accuracy report for development office; API/feed both directions."},
  angle="'Your next member lives four blocks away and asks their phone what to do Friday. Your late-night program should be the answer.'"),
 dict(g="Venues & Places", n="10 · Independent cinemas & screening rooms", src="est.",
  snap="Event-ization is the survival strategy: rep nights, Q&As, sing-alongs, local premieres. Showtimes are syndicated (Fandango-class) but EVENTS mostly aren't — the growth layer is the invisible layer. (Thin public data; validate.)",
  ch=["Commodity showtime listings everywhere; special events nowhere", "Competing with couches requires occasion-making", "Tiny teams; projectionist doubles as social manager"],
  gr=["Membership/loyalty growth via event programming", "Weeknight occupancy with rep/series brands", "Local partnerships (food, music) that need cross-promotion"],
  val=["Which special programming sells out, and who finds it how?", "Is your events calendar machine-readable anywhere?", "What's a member worth vs a ticket?"],
  recs={"S":"Series-brand support (Terror Tuesdays as an entity); event feed alongside showtime feed; member-signup on every listing."},
  angle="'Fandango has your showtimes. Nobody has your Wednesday cult night — least of all the AI your future regulars ask.'"),
 dict(g="Venues & Places", n="11 · Nontraditional & multi-use spaces (halls, churches, warehouses, record stores, bookstores)", src="est.",
  snap="The long tail where scenes actually incubate — in-store shows, house-adjacent venues, community halls. Zero marketing infrastructure by definition; presence is a flyer and a group chat. Highest per-entity impact for the agent. (Validate.)",
  ch=["No premises 'business identity' — often not even a Google listing", "Events are irregular; nothing recurring to anchor discovery", "Zero budget, zero staff, maximal authenticity"],
  gr=["Legitimacy without corporatization", "Bigger reach for occasional events without platform dependence", "Sustainable donations/door splits"],
  val=["What's the biggest crowd this room ever drew, and how?", "Would you want strangers, or is the group chat the point?", "Who 'runs' this space, actually?"],
  recs={"SO":"Respect the culture: opt-in visibility levels (public / listed-but-quiet); one-URL setup even from an IG only.",
        "S":"Claim flow that works with NO website at all — Instagram-only onboarding is the design bar."},
  angle="'You don't need to become a business to stop being invisible. You hold the string — including how visible you want to be.'"),
 # ---- ORGANIZERS & GROUPS ----
 dict(g="Organizers & Groups", n="12 · Festivals (music, arts, food, neighborhood)", src="AIF/Hypebot/MFW",
  snap="40+ cancellations in each of 2024 and 2025; core infrastructure costs +30–50% since 2019; sponsor pullback broke the mid-tier model. Survivors need earlier ticket velocity and year-round audience relationships, not bigger lineups.",
  ch=["Cost inflation (security, staging, insurance) with weather/permits risk", "Announce-spike-then-silence marketing rhythm; no year-round audience asset", "Sponsorship softness → earned revenue pressure"],
  gr=["Year-round community (the festival as membership, not weekend)", "Earlier presale velocity (cashflow = survival)", "Locals-first audience to derisk travel-dependent sales"],
  val=["What % must sell before you're safe, and by when?", "What do you say to your list in October?", "Which local audience never comes that should?"],
  recs={"S":"(Neighborhood fests) one-organizer edition; lineup announcements auto-kitted.",
        "M":"Artist-lineup cross-promotion (every booked act's agent announces the fest); countdown campaign kits.",
        "L":"Year-round content calendar from archive + lineup data; presale-velocity measurement in plain language."},
  angle="'Festivals die in the quiet months. A year-round, always-accurate presence — and every artist on your poster amplifying you automatically — costs nothing.'"),
 dict(g="Organizers & Groups", n="13 · Independent promoters & presenters", src="NIVA",
  snap="The connective tissue: book rooms they don't own, market shows they don't host. NIVA counts them in the 64%-unprofitable economy; they feel ticketing-giant pressure most directly. Their brand IS their calendar.",
  ch=["Split identity: their shows live under venues' names; brand equity leaks", "Per-show P&L brutality; one soft show erases a month", "Data scattered across venues' ticketing accounts"],
  gr=["A followable promoter brand (their taste as the product)", "Presale lift from owned audience, not just venue walk-in", "Better settlement position via provable draw"],
  val=["Do fans know it's YOUR show?", "What's your list size vs your average draw?", "Which venue relationship would improve if you brought 50 more presales?"],
  recs={"SO":"Promoter edition: their calendar across all rooms as one brand; scoped authority on their shows in any venue.",
        "S":"Series/brand pages + cross-venue analytics ('your Tuesday crowd follows you, not the room — here's proof')."},
  angle="'You build the night; the venue gets the Google result. Get your own front door — your whole calendar, every room, one brand, free.'"),
 dict(g="Organizers & Groups", n="14 · Community orgs, nonprofits & arts councils", src="AAM/Candid funding data",
  snap="Grant-shock downstream: the same federal cuts hitting museums hit local arts nonprofits, at smaller scale with thinner staff. They aggregate and produce culture (concert series, public art, classes) and are natural DISTRIBUTION PARTNERS (Mantle M-D/M-E), not just users.",
  ch=["Funding instability → staff cuts in exactly the outreach roles", "Event data trapped in PDFs and newsletters", "Mission metrics (participation) with no measurement capacity"],
  gr=["Provable community participation numbers (their grant currency)", "Younger participation", "Partnerships that stretch staff"],
  val=["What number do you report to funders, and how do you get it?", "Would you co-host a workshop for your members?", "What died in the last budget cut?"],
  recs={"S":"Free = mission-aligned; participation measurement as grant evidence; their calendar feed as a member benefit.",
        "M":"PARTNER track: train-the-trainer kits; their directory synced through us to everywhere."},
  angle="'Your mission is participation; your grant reports need numbers. Free tools for every member org — and the accuracy stats to prove the impact.'"),
 dict(g="Organizers & Groups", n="15 · Recurring-scene organizers (open mics, jams, poetry slams, song circles)", src="est.",
  snap="The weekly heartbeat of a scene, run by one devoted person, promoted by word of mouth and a laminated sign. Highest churn (nights die when the host burns out), zero data anywhere. The 'is it still on?' problem is THE problem. (Validate.)",
  ch=["'Is it still happening?' uncertainty kills attendance", "Host burnout = scene death; no institutional memory", "Zero budget, zero web presence beyond a post"],
  gr=["Reliable baseline attendance (enough signups to run)", "Succession/continuity when hosts rotate", "Recognition (these nights feed every other category's talent)"],
  val=["What happens to the night if you're sick?", "How many is a good night, and what makes it happen?", "Would a live 'yes it's on tonight' signal help?"],
  recs={"SO":"The 'still on' function is the killer feature (freshness signal front and center); recurring-series one-tap; host-rotation handoff."},
  angle="'Half the city thinks your open mic died in 2023. The other half never heard of it. Both fixed, free, in three taps.'"),
 dict(g="Organizers & Groups", n="16 · Social-dance & movement communities (salsa, swing, two-step, contra)", src="est.",
  snap="Growing post-pandemic (in-person hunger + TikTok dance discovery), organized through fragile channels (Facebook groups, WhatsApp). Classes + socials = recurring revenue events with a beginner-funnel problem. (Validate.)",
  ch=["Beginner funnel: newcomers can't find the entry-level night", "Venue instability (rooms change; the community must re-find itself)", "Organizer = instructor = promoter = one person"],
  gr=["Steady beginner intake (the community's lifeblood)", "Venue-change resilience", "Cross-scene traffic (salsa ↔ bachata ↔ zouk)"],
  val=["How does a total beginner find their first night?", "What happened last time you changed venues?", "Which class converts to socials best?"],
  recs={"SO":"Person-brand + movable-location handling ('follows the organizer, not the address'); beginner-tagged listings.",
        "S":"Class-to-social funnel kits; multi-teacher collectives as groups."},
  angle="'Your scene grows on beginners who almost didn't find it. Be findable the night someone finally decides to learn — everywhere they ask.'"),
 dict(g="Organizers & Groups", n="17 · Markets, fairs & pop-up organizers (makers, night markets, vintage)", src="est.",
  snap="Boomed with the creator/maker economy; an organizer aggregates dozens of SOLO vendors — one claim brings a whole roster into view. Weather/venue variability makes the freshness signal critical. (Validate.)",
  ch=["Every edition is a new logistics puzzle; marketing is the last task", "Vendor recruitment AND shopper attendance are both marketing problems", "Rain-date chaos destroys trust in listings"],
  gr=["Reliable shopper baseline so vendors keep coming", "Vendor waitlists (proof of health)", "Year-round brand between events"],
  val=["Which matters more this season: more shoppers or more vendors?", "What happens to attendance when you move or rain out?", "Do your vendors promote the market?"],
  recs={"S":"Organizer claim cascades: every vendor gets a lightweight presence + cross-promotion kit (23 entities from one signup).",
        "M":"Season-calendar sync + weather-update push that actually reaches the surfaces people check."},
  angle="'One signup makes your market — and every maker in it — findable. When it rains, everyone knows the new date in minutes.'"),
 # ---- ARTISTS & PEOPLE ----
 dict(g="Artists & People", n="18 · Bands & musical acts", src="MIDiA-class artist data",
  snap="Live = ~70% of income in the first five years; 77.8% earn under $15k/yr from music; only 13.3% live on music alone. Marketing time is unpaid time between day jobs. The number-one growth asset — the mailing list — is the least maintained.",
  ch=["Admin/promo burden on the one member who 'does the internet'", "Streaming pays nothing below scale (81% of catalog <1k streams)", "Draw is the booking currency, and they can't prove theirs"],
  gr=["Provable draw (gets rooms, gets guarantees)", "Direct fan channel (email/SMS) not owned by an algorithm", "Out-of-town anchors (first fans in the next city)"],
  val=["Who in the band does promo, and what does it cost them?", "Can you show a booker your draw?", "What's your list size vs your IG following?"],
  recs={"SO":"Artist edition core: dates-everywhere + facts-right + announcement kits; draw-proof stats for booking emails; never 'AI-powered' framing.",
        "S":"(Bands-as-business, 1-9) same + merch/list capture at every listing."},
  angle="'You didn't start a band to do data entry. Dates right everywhere, announcements made, your draw provable — free, and you approve everything.'"),
 dict(g="Artists & People", n="19 · Solo musicians & singer-songwriters", src="artist income data",
  snap="The largest single population in the supply universe (nonemployer by definition — the SOLO tier's archetype). Same economics as bands but every hour is theirs alone; residencies/regular gigs (restaurants, hotels, private) matter as much as shows.",
  ch=["One person = artist + agent + promoter + designer", "Gig types fragment (listening rooms, corporates, residencies) with different discovery", "Burnout is the churn"],
  gr=["Steady residency/private bookings (the rent-payers)", "A professional presence that books gigs while they sleep", "Slow-build fan list without content-treadmill guilt"],
  val=["What share of income is shows vs residencies vs private?", "What does a booker find when they search you?", "What would you drop first if something saved you 5 hours a week?"],
  recs={"SO":"EPK-view (LATER item) is aimed here; bookable-presence as the pitch ('what a booker finds'); minimum-viable content cadence."},
  angle="'Your presence should be booking you gigs while you're playing them. Three taps, free, and every date you play is right, everywhere.'"),
 dict(g="Artists & People", n="20 · DJs & electronic artists", src="nightlife + artist data",
  snap="Scene-network careers: residencies, guest slots, collectives. Nightlife contraction squeezes the room supply while the artist population grows. Brand lives on IG/SoundCloud/RA; gigs announced in stories that vanish in 24 hours.",
  ch=["Ephemeral announcement culture = zero durable presence", "Collective/alias complexity (three names, one person)", "Venue instability transfers to their calendar"],
  gr=["Residency stability + out-of-scene bookings (weddings-to-warehouses range)", "Alias/collective brand management", "Mix-to-gig funnel (listeners into rooms)"],
  val=["How many aliases/collectives do you juggle?", "Where does a promoter check you out?", "What share of gigs come from the scene network vs cold discovery?"],
  recs={"SO":"Multi-alias support under one claim; story-to-durable-listing capture; collective (group) edition ties members' dates."},
  angle="'Your set announcements die in 24 hours. Your presence shouldn't. Every alias, every room, one accurate you — free.'"),
 dict(g="Artists & People", n="21 · Comedians & spoken-word performers", src="est. + comedy boom",
  snap="Riding the comedy boom: more rooms, more mics, more paths (clips → tickets). Career = nightly presence across many rooms; the clip economy drives discovery but dates/rooms are chronically wrong online. (Validate.)",
  ch=["Plays 5 rooms a week; no listing keeps up", "Clip virality converts to tickets only if dates are findable at the moment of virality", "Road life = zero admin time"],
  gr=["Convert followers to butts-in-seats in each city", "Headline progression (mic → feature → headline) needs provable draw", "A durable home for 'where to see me'"],
  val=["When a clip pops, where do those people go?", "How do you tell your city you're headlining?", "What's your draw in your top three cities?"],
  recs={"SO":"High-frequency date sync (nightly changes); clip-moment readiness (link-in-bio always current); city-level draw stats."},
  angle="'The night your clip goes viral, 40,000 people wonder where to see you. Today the answer is a stale link. Fix it once, free.'"),
 dict(g="Artists & People", n="22 · Theater & dance companies, performance troupes", src="theater data",
  snap="Company-as-artist: project-based seasons, grant-dependent, venue-hopping. Same audience crisis as theaters (–34%/–44%) without a building's walk-by traffic. Every production is a cold-start marketing campaign.",
  ch=["No permanent address = no accumulated local presence", "Run-based rhythm: dark months then a three-week sprint", "Grant reporting demands audience data they can't produce"],
  gr=["A following that travels with the company between venues", "Younger/diverse audiences (existentially, as with theaters)", "Participation numbers for funders"],
  val=["How much of each run's audience is new vs returning?", "How do people find you between productions?", "What do you report to funders about reach?"],
  recs={"SO":"(Solo performers) person-brand edition.",
        "S":"Company edition: presence that persists between runs; production-launch kits; funder-ready participation stats."},
  angle="'Your company disappears between productions — to audiences and algorithms alike. Stay findable in the dark months, free.'"),
 dict(g="Artists & People", n="23 · Visual artists, makers & craft creators", src="est. + market data",
  snap="Sell through markets, fairs, studios, galleries, commissions — event-driven income without being 'performers.' Instagram is portfolio, storefront, and calendar at once; the art market's softness pushes direct-to-collector urgency. (Validate.)",
  ch=["Show/market schedule scattered; collectors can't follow the trail", "Platform dependence (IG algorithm = income volatility)", "Studio time vs promo time is a zero-sum war"],
  gr=["Direct collector list (the #1 de-platforming insurance)", "More/better market and fair placements", "Studio-visit and commission pipelines"],
  val=["Where are you showing next, and who knows?", "What share of sales come from repeat collectors?", "What did the last algorithm change do to your reach?"],
  recs={"SO":"Where-to-find-me edition (markets, fairs, open studios as 'dates'); collector-list capture on every listing; gallery cross-promotion."},
  angle="'Your collectors want to follow you — not fight an algorithm to find your next market. One accurate trail, everywhere, free.'"),
]

def esc(s): return s
def brief(c):
    tiers = {"SO":"SOLO","S":"SMALL","M":"MEDIUM","L":"LARGE","J":"JUMBO"}
    recs = "".join(f"<tr><td style='width:14%'><b>{tiers[k]}</b></td><td>{v}</td></tr>" for k,v in c["recs"].items())
    ch = "".join(f"<li>{x}</li>" for x in c["ch"])
    gr = "".join(f"<li>{x}</li>" for x in c["gr"])
    val = "".join(f"<li>{x}</li>" for x in c["val"])
    return f"""
<div class="cat">
<h3>{c['n']} <span class="srctag">[{c['src']}]</span></h3>
<p class="snap">{c['snap']}</p>
<table class="inner"><tr>
<td style="width:33%"><b>Key operational challenges</b><ul>{ch}</ul></td>
<td style="width:33%"><b>Growth initiatives &amp; desires</b><ul>{gr}</ul></td>
<td style="width:34%"><b>Validate in conversation</b><ul>{val}</ul></td>
</tr></table>
<table class="inner recs"><tr><th colspan="2">Recommendations by size</th></tr>{recs}</table>
<p class="angle"><b>Outreach angle:</b> {c['angle']}</p>
</div>"""

groups = {}
for c in CATS: groups.setdefault(c["g"], []).append(c)
briefs = ""
for g, items in groups.items():
    briefs += f"<h2>Part 3{'abc'[list(groups).index(g)]} · {g} ({len(items)})</h2>" + "".join(brief(c) for c in items)

css = """
@page { size: Letter; margin: 1.8cm 1.6cm;
  @bottom-center { content: "Category marketing research — 23 supply-side segments v2 · CONFIDENTIAL DRAFT · page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #888; } }
body { font-family: "DejaVu Sans", sans-serif; font-size: 8.9pt; line-height: 1.45; color: #0b0b0b; }
h1 { font-size: 16pt; border-bottom: 3px solid #0b0b0b; padding-bottom: 6px; }
h2 { font-size: 11.5pt; border-bottom: 1px solid #bbb; padding-bottom: 3px; margin-top: 18px; page-break-after: avoid; }
h3 { font-size: 9.8pt; margin: 0 0 4px 0; page-break-after: avoid; }
.sub { color: #52514e; font-size: 9.2pt; }
.srctag { font-size: 7.5pt; color: #52514e; font-weight: normal; }
.cat { border: 1px solid #ddd; border-left: 4px solid #2a78d6; padding: 8px 10px 6px; margin: 8px 0; page-break-inside: avoid; background: #fdfdfc; }
.snap { margin: 2px 0 6px 0; font-size: 8.6pt; }
table { border-collapse: collapse; width: 100%; }
table.inner td { border: 0.5pt solid #ccc; padding: 4px 6px; vertical-align: top; font-size: 8pt; }
table.inner th { background: #0b0b0b; color: #fff; padding: 3px 6px; text-align: left; font-size: 8pt; }
table.recs { margin-top: 4px; }
ul { margin: 3px 0 3px 14px; padding: 0; }
li { margin-bottom: 2px; }
.angle { font-size: 8.2pt; color: #333; margin: 5px 0 2px 0; }
table.plain td { border: 0.5pt solid #aaa; padding: 4px 6px; vertical-align: top; font-size: 8.2pt; }
table.plain th { background: #0b0b0b; color: #fff; padding: 4px 6px; text-align: left; font-size: 8.2pt; }
a { color: #0b5394; text-decoration: none; }
.note { background: #f4f4f2; border-left: 3px solid #2a78d6; padding: 7px 10px; font-size: 8.4pt; }
"""

body = f"""
<h1>Category marketing research: the 23 supply-side segments</h1>
<p class="sub">A category-specific research base for outreach and discovery conversations — challenges, goals, growth initiatives, validation questions, and recommendations by size within each category. Standalone working paper v2, 2026-08-01 (v2 splits bars from breweries/wineries/distilleries at founder direction, with their tastings/product-sales/education revenue model added; 22 becomes 23 categories). Companion to "How businesses actually run their marketing" (segment analysis v2). Sources cited inline; entries marked (Validate) rest on thinner public data and are explicitly hypotheses for the conversation program. No Wikipedia or forum sources.</p>

<h2>Part 0 · Before the research: what we need to consider knowing (the intelligence frame)</h2>
<p>The founder's directive asked what else we may need to consider knowing before compiling. Per category, beyond challenges/goals/initiatives, the outreach program needs twelve dimensions — the briefs below carry the first eight where data exists; the last four are largely UNKNOWABLE from desk research and are what the conversations must capture:</p>
<table class="plain">
<tr><th>Dimension</th><th>Why it matters for outreach</th><th>Source</th></tr>
<tr><td>1 · Population &amp; density per metro</td><td>Sizes the Austin motion; sets claim targets</td><td>Our source catalog + Census/NAICS — buildable now</td></tr>
<tr><td>2 · Revenue model &amp; margin structure</td><td>Frames value in THEIR unit (covers, tickets, commissions)</td><td>Industry reports (cited)</td></tr>
<tr><td>3 · Seasonality &amp; calendar rhythm</td><td>Times the outreach (approach festivals in their quiet months)</td><td>Industry + validate</td></tr>
<tr><td>4 · Decision-maker &amp; reachable moments</td><td>Who says yes and when they can listen</td><td>Partly known; validate</td></tr>
<tr><td>5 · Existing tech stack</td><td>Integration path (ticketing, POS, booking tools)</td><td>Validate + observation at claim time</td></tr>
<tr><td>6 · Discovery dependencies today</td><td>What we augment vs replace</td><td>Segment analysis v2 + validate</td></tr>
<tr><td>7 · Trigger moments</td><td>Openings, slow seasons, staff turnover, a viral moment</td><td>Validate</td></tr>
<tr><td>8 · Trust network &amp; watering holes</td><td>Associations (NIVA, arts councils), scene figures — the referral path</td><td>Partly known (Mantle M-D/M-E)</td></tr>
<tr><td>9 · Success metrics THEY use</td><td>Measurement must speak their language</td><td><b>Conversations</b></td></tr>
<tr><td>10 · Objections &amp; sensitivities</td><td>AI-wariness (artists), platform fatigue, 'another dashboard'</td><td><b>Conversations</b> (Part II §14 pre-registered)</td></tr>
<tr><td>11 · Willingness boundaries</td><td>What they will never automate (voice, community, booking)</td><td><b>Conversations</b></td></tr>
<tr><td>12 · Referral dynamics</td><td>Who they'd tell; what makes them tell</td><td><b>Conversations</b></td></tr>
</table>
<p class="note"><b>Also decided before compiling:</b> (a) the 23 categories below are PROPOSED — no canonical list existed in our documents; confirm or amend before the outreach program treats them as fixed; (b) size tiers within categories use the five-tier model from segment analysis v2 (SOLO/SMALL/MEDIUM/LARGE/JUMBO) — only tiers that meaningfully exist in a category get recommendations; (c) briefs deliberately mix sourced fact with labeled hypothesis, because the program's design is data → hypothesis → validated conversation, not data → assumption → pitch.</p>

<h2>Part 1 · The 23 categories (proposed)</h2>
<table class="plain">
<tr><th>Venues &amp; Places (11)</th><th>Organizers &amp; Groups (6)</th><th>Artists &amp; People (6)</th></tr>
<tr>
<td>1 Live music venues &amp; clubs<br/>2 Bars, pubs &amp; cocktail lounges<br/>3 Breweries, wineries, distilleries &amp; tasting rooms<br/>4 Restaurants &amp; cafés w/ events<br/>5 Theaters &amp; PACs<br/>6 Comedy clubs &amp; rooms<br/>7 Nightlife: dance clubs &amp; DJ rooms<br/>8 Galleries &amp; art spaces<br/>9 Museums &amp; institutions<br/>10 Independent cinemas<br/>11 Nontraditional &amp; multi-use spaces</td>
<td>12 Festivals<br/>13 Independent promoters &amp; presenters<br/>14 Community orgs &amp; arts councils<br/>15 Recurring-scene organizers (mics, jams, slams)<br/>16 Social-dance &amp; movement communities<br/>17 Markets, fairs &amp; pop-up organizers</td>
<td>18 Bands &amp; musical acts<br/>19 Solo musicians &amp; singer-songwriters<br/>20 DJs &amp; electronic artists<br/>21 Comedians &amp; spoken-word<br/>22 Theater/dance companies &amp; troupes<br/>23 Visual artists &amp; makers</td>
</tr></table>

<h2>Part 2 · The evidence base (cluster research, sourced)</h2>
<ul>
<li><b>Independent music venues/promoters/festivals:</b> <a href="https://www.nivassoc.org/stateoflive">NIVA State of Live</a> — 64% of independent venues unprofitable in 2024; $86.2B GDP contribution; rising rent/insurance/staffing/artist costs; ticketing-giant and resale pressure (<a href="https://routenote.com/blog/nivas-state-of-live-report-shows-independent-venues-are-essential-but-under-threat/">summary</a>).</li>
<li><b>Nightlife:</b> <a href="https://nielseniq.com/global/en/insights/analysis/2026/almost-three-late-night-hospitality-closures-every-week-in-last-six-years-of-pressure/">NIQ — late-night hospitality down 28.9% in six years (~3 net closures/week, UK)</a>; <a href="https://www.npr.org/2025/12/30/nx-s1-5658263/it-was-a-rough-year-for-nightclubs">NPR — a rough 2025 for US clubs (rents, declining drinking)</a>.</li>
<li><b>Restaurants/bars:</b> <a href="https://restaurant.org/research-and-media/research/research-reports/state-of-the-industry/">National Restaurant Association 2026 State of the Industry</a> — $1.55T sales; 9-in-10 operators cite food/labor/insurance/energy/swipe-fee pressure; <a href="https://www.restaurant365.com/guides/2026-state-of-the-restaurant-industry-mid-year-report/">staffing #1 challenge at 33% by mid-2026</a>.</li>
<li><b>Theaters/performing arts:</b> <a href="https://wallacefoundation.org/resource/article/three-years-after-pandemic-theaters-still-navigate-uncertain-waters">Wallace Foundation — audiences −34%, subscribers −44% vs 2019</a>; <a href="https://www.americantheatre.org/2025/01/14/meet-audiences-where-they-are/">American Theatre — subscription decay, aging/homogeneous audiences (NEA: 84% white)</a>.</li>
<li><b>Museums/institutions:</b> <a href="https://news.artnet.com/art-world/american-alliance-of-museums-survey-2025-2712464">AAM survey — bracing for a difficult 2026</a>; <a href="https://www.npr.org/2025/11/11/nx-s1-5604385/museums-attendance-donations-grants-trump">NPR — 55% below 2019 attendance; ⅓ lost federal grants, 67% couldn't replace</a>; <a href="https://www.theartnewspaper.com/2026/01/26/how-low-attendance-and-funding-cuts-forcing-united-states-museums-adapt">Art Newspaper — the turn to local audiences</a>.</li>
<li><b>Festivals:</b> <a href="https://www.hypebot.com/why-did-so-many-music-festivals-cancel-in-2025/">Hypebot — 40+ cancellations in 2024 and again 2025; infrastructure costs +30–50% since 2019; sponsor pullback broke the mid-tier model</a>; <a href="https://www.musicfestivalwizard.com/music-festivals-cancelled-in-2026/">MFW cancellation tracker</a>.</li>
<li><b>Breweries/wineries/distilleries:</b> <a href="https://www.brewersassociation.org/association-news/the-2025-year-in-beer/">Brewers Association 2025 Year in Beer — 434 closings vs 268 openings, second straight year of net contraction; the fight for occasions</a>; <a href="https://www.pressdemocrat.com/2026/06/11/silicon-valley-bank-dtc-wine-report/">SVB DTC Wine Report — tasting-room visits down (Napa −18%, Sonoma −8%, Paso −12%); club growth ~2% (Napa −4%)</a>; <a href="https://www.winebusiness.com/wbm/article/315325">Wine Business tasting-room survey — ~90% of club signups originate in the tasting room</a>; winery count 7,500 → 11,000 since 2019.</li>\n<li><b>Artists:</b> <a href="https://zipdo.co/indie-music-industry-statistics/">indie-artist compendium</a> — avg full-time indie income ~$32k; 77.8% under $15k/yr; 13.3% music-only; live ≈70% of early-career income; 81% of Spotify catalog under 1k streams.</li>
<li><b>Cross-segment marketing behavior:</b> segment analysis v2 (companion doc) — time/cash budgets, tactic mix, ROI-vs-adoption inversion.</li>
</ul>

{briefs}

<h2>Part 4 · Using this paper (the conversation program)</h2>
<ul>
<li><b>Sequence outreach by pain-freshness:</b> categories in acute, NAMED distress first (1, 6, 8, 11 — they have survey language for their pain) — the outreach echoes their own industry's numbers back to them, which reads as understanding, not selling.</li>
<li><b>Every conversation validates the brief:</b> the 'Validate' questions are the interview script seed; answers flow back into this paper (v2 becomes evidence-based where v1 is hypothesis).</li>
<li><b>Recommendations-by-size are the pitch calibration:</b> lead SOLO with time-return and control; SMALL with the Mirror and soft-night economics; MEDIUM with coherence across properties; LARGE/JUMBO with integration and reporting artifacts.</li>
<li><b>Partner categories (13, and associations in 1/4/8) are force multipliers</b> — approach as Mantle distribution partners, not just users.</li>
<li><b>Cross-category physics:</b> every brief's angle ends at the same promise — free, accurate, everywhere, you hold the string — so twenty-two conversations build ONE reputation.</li>
</ul>
"""

html = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"
HTML(string=html).write_pdf("Category_Research_23_Segments_v2.pdf")
print("written")
