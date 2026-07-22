#!/usr/bin/env python3
"""Generate design/proposals/direction-4-flow.html — FLOW v3.1 (static).

Founder round 8 (2026-07-22): "The pages are not rendering. All I see is
the map page." Root cause: the founder's file viewer executes NO
JavaScript — v3 rendered every card via JS, so only the static start
screen appeared (and v2.3's script-driven reveal was the same failure
wearing a different mask). The prototype must therefore be FULLY STATIC:

- Every card, lens, and list is baked into the HTML by this generator,
  all derived from the single SHOWS/VENUES dataset below (consistency by
  construction survives the loss of runtime rendering).
- Interactions use pure CSS: lenses open via :target (anchor links) and
  close via a link to a non-existent fragment (#_ clears :target without
  scrolling); the uncertainty sheet is <details>. Zero JS required for
  anything visible or tappable.
- A tiny progressive-enhancement <script> remains at the end: in a real
  browser it hides ended shows, tags live ones "on now", and stamps the
  clock. Without it the full evening renders, earliest first — complete
  information either way.

Run: python3 design/proposals/generate_flow.py  (writes the html beside
itself). Regenerate after every data or layout change; never hand-edit
the output.
"""
import html
import pathlib

import sys

OUT = (pathlib.Path(sys.argv[1]) if len(sys.argv) > 1
       else pathlib.Path(__file__).parent / "direction-4-flow.html")

AREAS = {
    "dt": {"name": "Downtown", "dot": (21, 26)},
    "rr": {"name": "Red River", "dot": (25, 22)},
    "e":  {"name": "East Side", "dot": (31, 30)},
    "s":  {"name": "South", "dot": (20, 40)},
}

VENUES = {
    "elephant":   dict(name="Elephant Room", area="dt", char="basement jazz cellar, candle-dark, standing", addr="315 Congress Ave", dist="0.4 mi", street="Congress Ave", site="elephantroom.com", special="Happy hour til 8 — well drinks $5", dot=(21, 26)),
    "saxon":      dict(name="Saxon Pub", area="s", char="small listening room, all ages of regulars", addr="1320 S Lamar", dist="2.6 mi", street="S Lamar", site="thesaxonpub.com", special=None, dot=(17, 38)),
    "continental":dict(name="Continental Club", area="s", char="50s dance hall, tight floor, no phones up front", addr="1315 S Congress", dist="1.8 mi", street="S Congress", site="continentalclub.com", special=None, dot=(20, 36)),
    "whitehorse": dict(name="The White Horse", area="e", char="two-step bar, free dance lessons early", addr="500 Comal St", dist="1.4 mi", street="E 6th", site="thewhitehorseaustin.com", special="Lone Star + well shot $7 all night", dot=(30, 28)),
    "farout":     dict(name="Far Out Lounge", area="s", char="big backyard stage under the oaks", addr="8504 S Congress", dist="4.8 mi", street="S Congress", site="thefaroutaustin.com", special=None, dot=(19, 45)),
    "stubbs":     dict(name="Stubb's", area="rr", char="outdoor amphitheater + BBQ inside", addr="801 Red River", dist="0.6 mi", street="Red River", site="stubbsaustin.com", special="Kitchen open til 11", dot=(25, 21)),
    "flamingo":   dict(name="Flamingo Cantina", area="e", char="reggae-rooted room, bleacher seats", addr="515 E 6th St", dist="0.6 mi", street="E 6th", site="flamingocantina.com", special=None, dot=(28, 27)),
    "mohawk":     dict(name="Mohawk", area="rr", char="indoor/outdoor stack, balcony views", addr="912 Red River", dist="0.5 mi", street="Red River", site="mohawkaustin.com", special=None, dot=(25, 20)),
    "coral":      dict(name="Coral Snake", area="e", char="narrow bar, loud back room", addr="2709 E Cesar Chavez", dist="1.0 mi", street="E Cesar Chavez", site="coralsnakebar.com", special="Mezcal happy hour til 10", dot=(33, 31)),
    "antones":    dict(name="Antone's", area="dt", char="home of the blues since 1975", addr="305 E 5th St", dist="0.3 mi", street="E 5th", site="antonesnightclub.com", special=None, dot=(22, 25)),
    "cheerup":    dict(name="Cheer Up Charlies", area="rr", char="queer-forward patio, two stages", addr="900 Red River", dist="0.8 mi", street="Red River", site="cheerupcharlies.com", special="Frozen ranch water $8", dot=(25, 22)),
    "sagebrush":  dict(name="Sagebrush", area="s", char="honky-tonk roadhouse, big floor, dancers welcome", addr="5500 S Congress", dist="2.1 mi", street="S Congress", site="sagebrushtexas.com", special="Late-nite taco truck on the patio til 1 AM", dot=(20, 41)),
    "volstead":   dict(name="The Volstead", area="e", char="velvet lounge beside the Hotel Vegas patio", addr="1500 E 6th St", dist="1.3 mi", street="E 6th", site="texashotelvegas.com", special=None, dot=(31, 29)),
    "speakeasy":  dict(name="Speakeasy", area="dt", char="three floors, rooftop over Congress", addr="412 Congress Ave", dist="0.4 mi", street="Congress Ave", site="speakeasyaustin.com", special="Rooftop opens 10 PM", dot=(21, 25)),
    "hotelvegas": dict(name="Hotel Vegas", area="e", char="garage-rock patio compound", addr="1502 E 6th St", dist="1.2 mi", street="E 6th", site="texashotelvegas.com", special=None, dot=(31, 28)),
    "parish":     dict(name="The Parish", area="dt", char="upstairs ballroom, famous ceiling, loud and close", addr="601 Brazos St", dist="0.7 mi", street="Brazos St", site="theparishaustin.com", special="Late-nite menu after midnight", dot=(24, 24)),
    "empire":     dict(name="Empire Control Room", area="rr", char="club room + garage stage", addr="606 E 7th St", dist="0.6 mi", street="Red River", site="empireatx.com", special=None, dot=(26, 23)),
}

SHOWS = [
    dict(id="s01", artist="Marfa Lights Trio", spark="brushes-and-upright jazz, conversation-quiet", start="19:30", doors=None, price="Free", genre="Jazz", v="elephant", hue=28, snips=["Desert Static", "Two Headlights"]),
    dict(id="s02", artist="The Deep End", spark="organ-trio soul jazz, simmering", start="20:00", doors=None, price="$10", genre="Jazz", v="saxon", hue=200, snips=["Undertow", "Green Hammond", "Last Call Waltz"]),
    dict(id="s03", artist="Hondo Wells", spark="barroom country, a voice like worn leather", start="20:30", doors=None, price="$8", genre="Honky-tonk", v="continental", hue=16, snips=["Bexar County Line", "Neon Novena"]),
    dict(id="s04", artist="Velvet Casket", spark="swamp-gospel stomp with brass and menace", start="21:00", doors="20:00", price="Free", genre="Gospel-punk", v="elephant", hue=12, snips=["Graveyard Hymn", "Brass Devil", "Low Water"]),
    dict(id="s05", artist="Silver Spur Sisters", spark="three-part harmony over pedal steel", start="21:00", doors=None, price="Free", genre="Honky-tonk", v="whitehorse", hue=40, snips=["Spur of the Moment", "Dancehall Dust"]),
    dict(id="s06", artist="Orquesta Nube", spark="nine-piece cumbia, horns like weather", start="21:00", doors=None, price="$12", genre="Cumbia", v="farout", hue=150, snips=["Nube Nueve", "Tormenta"]),
    dict(id="s07", artist="Knuckle Rose", spark="outlaw country with a punk backbeat", start="21:30", doors="20:30", price="$12", genre="Honky-tonk", v="stubbs", hue=350, snips=["Rose Tattoo", "Dead Man's Hand", "44 Blues"]),
    dict(id="s08", artist="La Marea", spark="coastal cumbia, accordion up front", start="21:30", doors=None, price="$10", genre="Cumbia", v="flamingo", hue=170, snips=["Marea Alta", "Sal y Sol"]),
    dict(id="s09", artist="Brass Ordinance", spark="street-brass gospel-punk, twelve feet of horn", start="22:00", doors=None, price="$10", genre="Gospel-punk", v="mohawk", hue=32, snips=["Ordinance 9", "Processional", "Third Ward Stomp"]),
    dict(id="s10", artist="Sonido Cascabel", spark="psychedelic cumbia, snake-rattle percussion", start="22:00", doors=None, price="Free", genre="Cumbia", v="coral", hue=130, snips=["Cascabel", "Vibora Verde"]),
    dict(id="s11", artist="Blue Prescription", spark="electric blues, heavy on the B-bender", start="22:00", doors="21:00", price="$15", genre="Jazz", v="antones", hue=220, snips=["Refill", "Night Nurse", "Downtown Dosage"]),
    dict(id="s12", artist="Bellhollow", spark="chorus-drenched shoegaze, slow-blooming", start="22:15", doors=None, price="Free", genre="Shoegaze", v="cheerup", hue=280, snips=["Hollow Bell", "Fadeout"]),
    dict(id="s13", artist="Reina Cortez y Los Fantasmas", spark="cumbia noir — organ smoke over a two-step", start="22:30", doors=None, price="$12", genre="Cumbia", v="sagebrush", hue=190, snips=["Fantasma Mío", "Órgano Negro"]),
    dict(id="s14", artist="Moon Court", spark="late-night modal jazz, hushed and electric", start="22:30", doors=None, price="Free", genre="Jazz", v="volstead", hue=240, snips=["Recess", "Lunar Docket"]),
    dict(id="s15", artist="DJ Cielo", spark="Latin trap into house, rooftop set", start="23:00", doors=None, price="$10", genre="Hip-hop", v="speakeasy", hue=300, snips=["Cielo Abierto"]),
    dict(id="s16", artist="The Ninth Hour", spark="doom-gospel choir over punk drums", start="23:00", doors=None, price="$8", genre="Gospel-punk", v="hotelvegas", hue=8, snips=["Nona", "Canonical"]),
    dict(id="s17", artist="Glass Anthem", spark="shoegaze wall, patient and enormous", tier="c", start="23:45", doors="23:00", price="$15", genre="Shoegaze", v="parish", hue=260, snips=["Pale Cathedral"]),
    dict(id="s18", artist="Vantablonde", spark="blackout-pop rap, strobe-lit", start="24:00", doors=None, price="$12", genre="Hip-hop", v="empire", hue=320, snips=["Vanta", "Peroxide"]),
]

NEARBY = {
    "dt": dict(title="Near Downtown rooms", sub="Congress to Brazos — dense blocks, easy walking",
               streets="M20 0v80M50 0v80M80 0v80M110 0v80M140 0v80M0 20h160M0 44h160M0 68h160",
               spots=[("Small Victory", "cocktail bar", "350 ft · 1-min walk", 66, 34),
                      ("Easy Tiger", "beer garden + bakery", "400 ft · 2-min walk", 103, 38),
                      ("La Condesa", "restaurant, late kitchen", "0.2 mi · 4-min walk", 58, 60),
                      ("Voodoo Doughnut", "late-nite food", "0.2 mi · 4-min walk", 118, 58)],
               note="Under half a mile: walk. Rainey or East 6th: pedicab. South Congress: ride."),
    "rr": dict(title="Near Red River rooms", sub="the club strip — everything within a few blocks",
               streets="M30 0v80M65 0v80M100 0v80M135 0v80M0 24h160M0 48h160",
               spots=[("Easy Tiger", "beer garden", "0.2 mi · 4-min walk", 60, 30),
                      ("Voodoo Doughnut", "late-nite food", "0.3 mi · 6-min walk", 52, 60),
                      ("Casino El Camino", "burgers til late", "0.3 mi · 6-min walk", 110, 34),
                      ("Hoboken Pie", "slices til 3 AM", "0.2 mi · 4-min walk", 96, 62)],
               note="All walkable; pedicab if you cross I-35 to the East Side."),
    "e":  dict(title="Near East Side rooms", sub="E 6th and Cesar Chavez — flat, bikeable, patio-dense",
               streets="M20 0v80M60 0v80M100 0v80M140 0v80M0 30h160M0 58h160",
               spots=[("Whisler's", "cocktail bar", "0.2 mi · 4-min walk", 60, 26),
                      ("Cuantos Tacos", "late-nite tacos", "0.2 mi · 4-min walk", 96, 28),
                      ("Zilker Brewing", "taproom", "0.3 mi · 6-min walk", 56, 64),
                      ("Justine's", "late French kitchen", "0.9 mi · pedicab ~5 min", 126, 66)],
               note="Walk the near blocks; pedicabs run E 6th; ride back downtown ~7 min."),
    "s":  dict(title="Near South rooms", sub="S Congress and S Lamar — spread out, plan the hop",
               streets="M80 0v80M30 0l20 80M130 0l-20 80M0 30h160M0 60h160",
               spots=[("Cosmic Coffee + Beer", "garden bar, food trucks", "0.3 mi · 6-min walk", 70, 24),
                      ("Little Darlin'", "bar, backyard", "0.5 mi · 10-min walk", 96, 66),
                      ("Torchy's SoCo", "late tacos", "0.4 mi · 8-min walk", 52, 58),
                      ("Downtown", "everything else tonight", "ride ~12 min", 80, 8)],
               note="This stretch is spread out — walk the near spots, pedicab the strip, ride downtown."),
}

E = html.escape


def t_min(t):
    h, m = map(int, t.split(":"))
    if h < 5:
        h += 24
    return h * 60 + m


def t_fmt(t):
    h, m = map(int, t.split(":"))
    h %= 24
    ap = "PM" if h >= 12 else "AM"
    h = h % 12 or 12
    return f"{h}:{m:02d} {ap}"


def austin_svg(dot):
    return (f'<svg viewBox="0 0 44 50">'
            f'<path class="austin-shape" d="M17 2l9 1 4 5 8 3-1 8 5 6-6 8 1 9-8 5-9-1-6-6 1-8-6-6 3-8-2-6z"/>'
            f'<path class="austin-river" d="M2 20q10 3 16 7t24 9"/>'
            f'<circle class="austin-ring" cx="{dot[0]}" cy="{dot[1]}" r="5"/>'
            f'<circle class="austin-dot" cx="{dot[0]}" cy="{dot[1]}" r="2.6"/></svg>')


def art_photo(hue, label, cls="aphoto"):
    return (f'<figure class="ph {cls}"><svg viewBox="0 0 160 60" preserveAspectRatio="xMidYMid slice">'
            f'<rect width="160" height="60" fill="hsl({hue} 36% 15%)"/>'
            f'<polygon points="80,0 40,60 120,60" fill="hsl({hue} 70% 70%)" opacity=".13"/>'
            f'<ellipse cx="80" cy="57" rx="52" ry="5" fill="hsl({hue} 70% 70%)" opacity=".12"/>'
            f'<path d="M64 34q4-10 8-10t7 9l2 27h-19z" fill="#0A0709"/><circle cx="73" cy="20" r="5.6" fill="#0A0709"/>'
            f'<path d="M94 38q3-8 6-8t6 8l2 22h-16z" fill="#0A0709"/><circle cx="100" cy="26" r="4.8" fill="#0A0709"/>'
            f'</svg><figcaption>{E(label)}</figcaption></figure>')


def ven_photo(hue, go_label=True):
    go = '<span class="go">venue ›</span>' if go_label else ""
    return (f'<div class="vphoto" aria-hidden="true">{go}<svg viewBox="0 0 160 40" preserveAspectRatio="xMidYMid slice">'
            f'<rect width="160" height="40" fill="hsl({hue} 25% 11%)"/>'
            f'<path d="M18 40V18q62-13 124 0v22z" fill="hsl({hue} 24% 8%)"/>'
            f'<circle cx="48" cy="24" r="1.8" fill="#FFC77D"/><circle cx="80" cy="21" r="1.8" fill="#FFC77D"/>'
            f'<circle cx="114" cy="24" r="1.8" fill="#FFC77D"/>'
            f'<ellipse cx="80" cy="33" rx="38" ry="2.6" fill="#FFC77D" opacity=".2"/></svg></div>')


def slug(g):
    return g.lower().replace(" ", "-")


# The local truth boundary EVERY lens carries (evaluator r3, PR #45): each
# lens is deep-linkable (#a-s01, #g-jazz, ...), so a disclaimer elsewhere
# on the page does not fail closed — the boundary must be on the surface
# itself. Rendered by construction into every lens builder;
# tests/test_flow_static_integrity.py fails any lens without it.
FIXNOTE = ('<p class="fixnote">Prototype sample — fictional listings staged '
           'at real venues; details illustrative, not verified.</p>')


genre_counts, area_counts = {}, {}
for s in SHOWS:
    genre_counts[s["genre"]] = genre_counts.get(s["genre"], 0) + 1
    a = VENUES[s["v"]]["area"]
    area_counts[a] = area_counts.get(a, 0) + 1
venue_count = len({s["v"] for s in SHOWS})
ordered = sorted(SHOWS, key=lambda s: t_min(s["start"]))


def card(s):
    v = VENUES[s["v"]]
    tier_c = s.get("tier") == "c"
    doors = f' <span class="doors">· doors {t_fmt(s["doors"])}</span>' if s.get("doors") else ""
    snips = "".join(f'<span class="chip snip"><i>♪</i>{E(t)}</span>' for t in s["snips"])
    # Provenance truth (evaluator r1, PR #45): these are FIXTURES — fictional
    # shows and invented specials staged at real venues. The visible labels
    # must say so; a prototype may not attribute fabricated data to a real
    # business as sourced fact.
    special = (f'<span class="vspecial"><small>venue special — sample, not from the venue</small>{E(v["special"])}</span>'
               if v["special"] else "")
    unc_text = (
        "Sample card — this show is a prototype fixture, not a real listing, "
        "and the venue details shown (distance, street, description) are "
        "illustrative too. In the product this panel shows the listing's real "
        "source and when it was last seen, with the venue's own site as the "
        "last word"
        + (" — this card demonstrates the low-confidence ✳ register (one source so far)"
           if tier_c else "")
        + ". Venue site: ")
    spark = f'{"✳ " if tier_c else ""}{E(s["spark"])}{" <small>— first notes</small>" if tier_c else ""}'
    return f'''
  <section class="room" id="{s["id"]}" data-start="{s["start"]}"
    style="--bg:radial-gradient(140% 110% at 40% 0%, hsl({s["hue"]} 30% 16%) 0%, hsl({s["hue"]} 20% 7%) 70%)">
    {art_photo(s["hue"], s["artist"])}
    <a class="zone z-artist" href="#a-{s["id"]}" aria-label="Artist: {E(s["artist"])}">
      <span class="go">artist ›</span>
      <h2 class="who">{E(s["artist"])}</h2>
      <p class="times">{t_fmt(s["start"])}{doors}<span class="livetag"></span></p>
      <p class="spark{" tierc" if tier_c else ""}">{spark}</p>
    </a>
    <div class="snips">{snips}</div>
    <div class="z-venue">
      <a class="vlink" href="#v-{s["v"]}" aria-label="Venue: {E(v["name"])}">
      {ven_photo(s["hue"])}
      <span class="vrow">
        <span class="minimap" aria-hidden="true">{austin_svg(v["dot"])}</span>
        <span class="vtext"><span class="vname">{E(v["name"])}</span>
          <span class="vchar">{E(v["char"])}</span>
          <span class="vmeta">{E(v["addr"])} · {v["dist"]}</span></span>
      </span></a>
      <div class="vfoot">
        {special}
        <a class="vnearby" href="#n-{v["area"]}">See nearby ›</a>
        <a class="vsite" href="https://{v["site"]}" target="_blank" rel="noopener">{v["site"]}&thinsp;↗</a>
      </div>
    </div>
    <div class="rail">
      <span class="chip{" free" if s["price"] == "Free" else ""}">{s["price"]}</span>
      <a class="chip genre" href="#g-{slug(s["genre"])}">{E(s["genre"])} <b>{genre_counts[s["genre"]]}</b></a>
      <details class="unc"><summary aria-label="Something off? How we know">?</summary>
        <div class="sheet" role="dialog" aria-label="How we know"><p>{unc_text}<a href="https://{v["site"]}">{v["site"]}</a> <em>(tap ? again to close)</em></p></div></details>
    </div>
  </section>'''


def artist_lens(s):
    v = VENUES[s["v"]]
    tier_c = s.get("tier") == "c"
    doors = f' (doors {t_fmt(s["doors"])})' if s.get("doors") else ""
    spark = f'{"✳ " if tier_c else ""}{E(s["spark"])}{" <small>— first notes</small>" if tier_c else ""}'
    snips = "".join(f'<span class="chip snip"><i>♪</i>{E(t)}</span>' for t in s["snips"])
    return f'''
<section class="lens" id="a-{s["id"]}" role="region" aria-label="Artist: {E(s["artist"])}">
  <a class="chip back" href="#{s["id"]}">‹ Back</a><a class="chip switch" href="#v-{s["v"]}">the venue ›</a>
  {FIXNOTE}
  {art_photo(s["hue"], s["artist"], cls="")}
  <h3 class="who">{E(s["artist"])}</h3>
  <p class="spark{" tierc" if tier_c else ""}">{spark}</p>
  <dl><dt>Tonight</dt><dd>{t_fmt(s["start"])}{doors} · {s["price"]} · {E(v["name"])}</dd>
  <dt>Genre</dt><dd><a href="#g-{slug(s["genre"])}">{E(s["genre"])} — {genre_counts[s["genre"]]} playing tonight</a></dd></dl>
  <div class="snips">{snips}</div>
</section>'''


def venue_lens(vk):
    v = VENUES[vk]
    here_shows = sorted((s for s in SHOWS if s["v"] == vk), key=lambda s: t_min(s["start"]))
    hue = here_shows[0]["hue"]
    here = " · ".join(f'<a href="#a-{s["id"]}">{E(s["artist"])} {t_fmt(s["start"])}</a>' for s in here_shows)
    special = (f'<p class="vspecial" style="margin-top:12px"><small>venue special — sample, not from the venue</small>{E(v["special"])}</p>'
               if v["special"] else "")
    back = f'#{here_shows[0]["id"]}'
    return f'''
<section class="lens" id="v-{vk}" role="region" aria-label="Venue: {E(v["name"])}">
  <a class="chip back" href="{back}">‹ Back</a>
  {FIXNOTE}
  <figure class="ph" style="height:clamp(100px,16dvh,160px)">{ven_photo(hue, go_label=False)}<figcaption>{E(v["name"])}</figcaption></figure>
  <h3 class="who">{E(v["name"])}</h3><p class="spark">{E(v["char"])}</p>
  <p class="gnote" style="margin:2px 0 8px">Sample venue details — the address, distance, and description here are illustrative for this prototype, not verified facts about the business. The product draws them from a sourced, freshness-stamped pipeline.</p>
  <div class="mapline"><span class="minimap" aria-hidden="true">{austin_svg(v["dot"])}</span>
  <dl style="margin:0"><dt>Address</dt><dd>{E(v["addr"])} · {v["dist"]}</dd>
  <dt>Tonight here</dt><dd>{here}</dd>
  <dt>Their site</dt><dd><a href="https://{v["site"]}" target="_blank" rel="noopener">{v["site"]}&thinsp;↗</a></dd></dl></div>
  {special}
  <div class="rail" style="margin-top:14px"><a class="vnearby" href="#n-{v["area"]}">See nearby ›</a></div>
</section>'''


def row(s, with_genre=False):
    v = VENUES[s["v"]]
    extra = f' · {E(s["genre"])}' if with_genre else ""
    return (f'<a class="gcard" href="#{s["id"]}" data-start="{s["start"]}">'
            f'<span class="gwho">{E(s["artist"])}</span><span class="livetag"></span>'
            f'<span class="gmeta"><b>{E(v["name"])}</b> · {t_fmt(s["start"])}{extra} · {s["price"]}'
            f'<br>{v["dist"]} · {E(v["street"])}</span></a>')


def genre_lens(g):
    rows = sorted((s for s in SHOWS if s["genre"] == g), key=lambda s: t_min(s["start"]))
    n = len(rows)
    return (f'<section class="lens" id="g-{slug(g)}" role="region" aria-label="{E(g)} tonight">'
            f'<a class="chip back" href="#_">‹ Back</a>{FIXNOTE}'
            f'<h3 class="who">{E(g)} tonight</h3><p class="spark">{n} show{"s" if n > 1 else ""}, by start time</p>'
            + "".join(row(s) for s in rows) + '</section>')


def area_lens(k):
    rows = sorted((s for s in SHOWS if VENUES[s["v"]]["area"] == k), key=lambda s: t_min(s["start"]))
    n = len(rows)
    return (f'<section class="lens" id="ar-{k}" role="region" aria-label="{E(AREAS[k]["name"])} tonight">'
            f'<a class="chip back" href="#_">‹ Back</a>{FIXNOTE}'
            f'<h3 class="who">{E(AREAS[k]["name"])} tonight</h3><p class="spark">{n} show{"s" if n > 1 else ""}, by start time</p>'
            + "".join(row(s, with_genre=True) for s in rows) + '</section>')


def nearby_lens(k):
    nb = NEARBY[k]
    dots = "".join(f'<circle class="near-spot" cx="{x}" cy="{y}" r="2.6"/>'
                   f'<text class="near-label" x="{x}" y="{y - 5}" text-anchor="middle">{E(name.upper())}</text>'
                   for name, _, _, x, y in nb["spots"])
    cards = "".join(f'<div class="ncard"><span class="nwho">{E(name)}</span><span class="ntype">{E(typ)}</span>'
                    f'<span class="nhow">{E(how)}</span></div>' for name, typ, how, _, _ in nb["spots"])
    return f'''
<section class="lens" id="n-{k}" role="region" aria-label="{E(nb["title"])}">
  <a class="chip back" href="#_">‹ Back</a>
  {FIXNOTE}
  <h3 class="who">{E(nb["title"])}</h3><p class="spark">{E(nb["sub"])}</p>
  <p class="gnote" style="margin:2px 0 8px">Sample guidance — these businesses are real, but every distance, walk time, transport suggestion, and hours claim here is illustrative for this prototype, not verified. The product draws nearby data live from the mapping layer with freshness shown.</p>
  <div class="nearmap" aria-hidden="true"><svg viewBox="0 0 160 80">
    <path class="near-street" d="{nb["streets"]}"/>
    <circle class="near-ring" cx="80" cy="44" r="34"/><text class="near-label" x="80" y="12" text-anchor="middle">— 5-MIN WALK —</text>
    <circle class="near-venue" cx="80" cy="44" r="4"/>{dots}
  </svg></div>
  {cards}
  <p class="gnote">{E(nb["note"])}</p>
</section>'''


# ---- The Ask layer (founder round 9: "voice ability for the site to
# surface options based on someone's desires - as captured in prior
# sessions"). Canon: docs/strategy/ONE_LIVE_MEMBER_PREFERENCES_v1.md —
# personalization is a LENS never a GATE; every recommendation carries
# provenance; preference data is the member's alone, never sold, never
# ranking anyone else's feed. Static-first: desire chips anchor to
# pre-computed result lenses; voice is a browser enhancement that lands
# on the same lenses. "Prior sessions" memory here is a SAMPLE of the
# P1 "My defaults" on-device layer.
def _dist_mi(v):
    return float(v["dist"].split()[0])


def _price_num(s):
    return 0 if s["price"] == "Free" else int(s["price"].lstrip("$"))


# Venues whose fixture data includes food (drives "dinner and a show").
_FOOD = {
    "stubbs": "BBQ inside, kitchen open til 11 (sample)",
    "sagebrush": "taco truck on the patio til 1 AM (sample)",
    "parish": "late-nite menu after midnight (sample)",
}
_OUTDOOR_WORDS = ("outdoor", "backyard", "amphitheater", "patio", "oaks")
# Sample memory: rooms the member has already been (drives "somewhere new").
_BEEN = ("elephant", "sagebrush")

# Chips are phrased as the example searches a member would actually say —
# each one is a pre-computed lens (founder round 10: "more expansive in
# terms of options - use the example searches to guide the options").
DESIRES = {
    "cheapclose": dict(
        label="“Cheap and close by”",
        title="Cheap and close tonight",
        match=lambda s: _price_num(s) <= 10 and _dist_mi(VENUES[s["v"]]) <= 1.0,
        why=lambda s: f'{s["price"]} · {VENUES[s["v"]]["dist"]} away',
        memory=None),
    "free": dict(
        label="“Something free tonight”",
        title="Free tonight",
        match=lambda s: s["price"] == "Free",
        why=lambda s: f'Free · {VENUES[s["v"]]["dist"]} · {s["genre"]}',
        memory=None),
    "dance": dict(
        label="“Somewhere to dance”",
        title="Dance floors tonight",
        match=lambda s: s["genre"] in ("Cumbia", "Honky-tonk"),
        why=lambda s: f'{s["genre"]} · {VENUES[s["v"]]["char"].split(",")[0]}',
        memory="you two-stepped at Sagebrush two Fridays running"),
    "quiet": dict(
        label="“A quiet spot for a date”",
        title="Quiet rooms tonight",
        match=lambda s: s["genre"] == "Jazz",
        why=lambda s: f'{s["genre"]} · {VENUES[s["v"]]["char"].split(",")[0]}',
        memory="you saved two candle-lit listening rooms"),
    "loud": dict(
        label="“Loud guitars, close to the stage”",
        title="Loud rooms tonight",
        match=lambda s: s["genre"] in ("Shoegaze", "Gospel-punk"),
        why=lambda s: f'{s["genre"]} · {VENUES[s["v"]]["char"].split(",")[0]}',
        memory="you stay past midnight when the room is loud"),
    "dinner": dict(
        label="“Dinner and a show”",
        title="Dinner and a show tonight",
        match=lambda s: s["v"] in _FOOD,
        why=lambda s: _FOOD[s["v"]],
        memory=None),
    "outdoors": dict(
        label="“Outside under the lights”",
        title="Open-air rooms tonight",
        match=lambda s: any(w in VENUES[s["v"]]["char"] for w in _OUTDOOR_WORDS),
        why=lambda s: VENUES[s["v"]]["char"].split(",")[0],
        memory=None),
    "late": dict(
        label="“Starting late”",
        title="Late starts tonight",
        match=lambda s: t_min(s["start"]) >= t_min("22:30"),
        why=lambda s: f'{t_fmt(s["start"])} start · {s["genre"]}',
        memory="you usually head out after 10"),
    "new": dict(
        label="“Somewhere I haven't been”",
        title="New rooms for you",
        match=lambda s: s["v"] not in _BEEN,
        why=lambda s: f'{VENUES[s["v"]]["name"]} — not in your nights yet',
        memory="you've been to Elephant Room and Sagebrush; these are new"),
}


def ask_result_lens(key):
    d = DESIRES[key]
    rows = sorted((s for s in SHOWS if d["match"](s)), key=lambda s: t_min(s["start"]))
    mem = (f' · <em>{E(d["memory"])} (sample memory)</em>' if d["memory"] else "")
    body = "".join(
        f'<a class="gcard" href="#{s["id"]}" data-start="{s["start"]}">'
        f'<span class="gwho">{E(s["artist"])}</span><span class="livetag"></span>'
        f'<span class="gmeta"><b>{E(VENUES[s["v"]]["name"])}</b> · {t_fmt(s["start"])} · {s["price"]}</span>'
        f'<span class="gwhy">why: {E(d["why"](s))}{mem}</span></a>'
        for s in rows)
    return (f'<section class="lens" id="ask-{key}" role="region" aria-label="{E(d["title"])}">'
            f'<a class="chip back" href="#ask">‹ Back</a>{FIXNOTE}'
            f'<h3 class="who">{E(d["title"])}</h3>'
            f'<p class="spark">{len(rows)} match{"es" if len(rows) != 1 else ""}, by start time</p>'
            f'<p class="gnote" style="margin:2px 0 4px">A lens, never a gate — this narrows nothing away; '
            f'the full night stays one Back-tap below. Every match says why.</p>'
            + body + '</section>')


ASK_LENS = f'''
<section class="lens" id="ask" role="region" aria-label="Ask for tonight">
  <a class="chip back" href="#_">‹ Back</a>
  {FIXNOTE}
  <h3 class="who">What are you feeling?</h3>
  <p class="spark">Tell me or tap below</p>
  <div class="rail" style="padding:0;margin:10px 0 2px">
    <button class="chip" id="micbtn" type="button" hidden><svg class="glyph" viewBox="0 0 20 20"><path d="M10 2a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3zm-5 8a5 5 0 0 0 10 0h1.6a6.6 6.6 0 0 1-5.8 6.55V19H8.2v-2.45A6.6 6.6 0 0 1 3.4 10z" fill="currentColor"/></svg>Tell me what to find</button>
    <span class="gnote" id="voicenote">Voice works in a browser (Safari: tap "Tell me what to find" and allow the mic). The options below do the same thing by touch.</span>
  </div>
  <p class="gnote" id="heard" style="min-height:1em"></p>
  <div class="desires">
    {"".join(f'<a class="chip" href="#ask-{k}">{E(d["label"])}</a>' for k, d in DESIRES.items())}
  </div>
  <div class="memory">
    <small>from your prior nights — sample memory</small>
    Your scene so far: candle-lit jazz rooms and cumbia floors · usually out after 10 · Downtown and East.
    <span class="gnote" style="display:block;margin-top:6px">In the product this is your on-device "My defaults" plus your saves — provenance shown on every suggestion ("because you saved…"), yours alone, never sold, never used to rank anyone else's feed.</span>
  </div>
</section>''' + "".join(ask_result_lens(k) for k in DESIRES)

sky_parts = "".join(
    f'<a class="part" href="#ar-{k}" aria-label="{E(a["name"])}: {area_counts.get(k, 0)} shows tonight">'
    f'<circle cx="{a["dot"][0]}" cy="{a["dot"][1]}" r="{4.5 + area_counts.get(k, 0) * 0.35:.1f}"/>'
    f'<text x="{a["dot"][0]}" y="{a["dot"][1] - 1}" text-anchor="middle">{E(a["name"].upper())}</text>'
    f'<text class="n" x="{a["dot"][0]}" y="{a["dot"][1] + 4}" text-anchor="middle">{area_counts.get(k, 0)}</text></a>'
    for k, a in AREAS.items())

sky_chips = "".join(
    f'<a class="chip" href="#g-{slug(g)}">{E(g)}<b>{n}</b></a>'
    for g, n in sorted(genre_counts.items(), key=lambda kv: -kv[1]))

cards_html = "".join(card(s) for s in ordered)
lenses_html = ("".join(artist_lens(s) for s in ordered)
               + "".join(venue_lens(vk) for vk in VENUES if any(s["v"] == vk for s in SHOWS))
               + "".join(genre_lens(g) for g in genre_counts)
               + "".join(area_lens(k) for k in AREAS)
               + "".join(nearby_lens(k) for k in NEARBY)
               + ASK_LENS)

page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>ONE LIVE — Direction 4: FLOW v3.1 (static prototype)</title>
<!-- GENERATED by generate_flow.py — do not hand-edit. FLOW v3.1: fully
  static HTML+CSS (founder's viewer runs no JavaScript); lenses open via
  CSS :target anchors; the optional script at the end only enhances
  (clock filtering) in real browsers. -->
<style>
  :root{{
    --ink:#F4EFE6; --dim:#BDB5A6; --night:#0B0B10; --night2:#15151D;
    --ember:#FF7A45; --glow:#FFC77D; --mint:#CFF5E2; --river:#7FB4D6;
    --safe-t:env(safe-area-inset-top,0px); --safe-b:env(safe-area-inset-bottom,0px);
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  html{{scroll-behavior:smooth}}
  body{{background:var(--night);color:var(--ink);font:15.5px/1.42 "Space Grotesk",system-ui,sans-serif}}
  a{{color:inherit;text-decoration:none}}
  .masthead{{position:sticky;top:0;z-index:6;display:flex;justify-content:space-between;align-items:baseline;
    padding:calc(var(--safe-t) + 10px) 18px 10px;background:linear-gradient(#0B0B10f2,#0B0B10e6 70%,transparent);backdrop-filter:blur(8px)}}
  .masthead h1{{font-size:14px;letter-spacing:.14em;text-transform:uppercase;font-weight:600}}
  .masthead .now{{font-size:11.5px;color:var(--dim)}}
  .sky{{position:relative;min-height:88dvh;display:flex;flex-direction:column;align-items:center;
    justify-content:center;gap:10px;padding:10px 16px 24px;text-align:center}}
  .sky h2{{font-family:Georgia,serif;font-size:clamp(22px,6vw,29px)}}
  .sky .sub{{color:var(--dim);font-size:13.5px}}
  .citymap{{width:min(74vw,330px)}}
  .citymap svg{{width:100%;height:auto;display:block}}
  .austin-shape{{fill:#ffffff0d;stroke:#BDB5A6;stroke-width:.9}}
  .austin-river{{fill:none;stroke:var(--river);stroke-width:1.2;opacity:.85}}
  .austin-dot{{fill:var(--ember)}} .austin-ring{{fill:none;stroke:var(--ember);opacity:.5}}
  .part circle{{fill:#FF7A4522;stroke:#FF7A4577;stroke-width:.7}}
  .part:active circle{{fill:#FF7A4544}}
  .part text{{fill:var(--ink);font:600 3.4px "Space Grotesk",system-ui,sans-serif;letter-spacing:.04em}}
  .part text.n{{fill:var(--glow);font-size:4.6px;font-weight:700}}
  .constellation{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:360px}}
  .constellation .chip b{{color:var(--glow);font-weight:700;margin-left:5px}}
  .room{{position:relative;min-height:70dvh;margin:0 10px 12px;border-radius:20px;overflow:hidden;
    display:flex;flex-direction:column;justify-content:flex-end;gap:2px;padding:14px 14px 12px;isolation:isolate}}
  .room::before{{content:"";position:absolute;inset:0;z-index:-2;background:var(--bg,#181822)}}
  .room::after{{content:"";position:absolute;inset:0;z-index:-1;opacity:.4;mix-blend-mode:overlay;pointer-events:none;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)' opacity='.35'/%3E%3C/svg%3E")}}
  .room.gone{{display:none}}
  .ph{{position:relative;border-radius:12px;overflow:hidden;background:#000;display:block}}
  .ph svg{{width:100%;height:100%;display:block}}
  .ph figcaption{{position:absolute;left:8px;bottom:6px;font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
    color:#F4EFE6;background:#000000a8;padding:3px 8px;border-radius:999px}}
  .aphoto{{height:clamp(76px,10dvh,110px);margin-bottom:6px}}
  .zone{{border-radius:14px;padding:10px 12px;position:relative;display:block}}
  .zone:active{{background:#ffffff10}}
  .zone .go,.vphoto .go{{position:absolute;right:10px;top:12px;color:var(--dim);font-size:13px}}
  .z-artist .who{{font-family:Georgia,serif;font-size:clamp(24px,6.6vw,31px);line-height:1.05;margin-bottom:2px;padding-right:64px}}
  .times{{color:var(--glow);font-weight:600;font-size:14.5px;margin-bottom:3px}}
  .times .doors{{color:var(--dim);font-weight:400}}
  .livetag{{color:var(--mint);font-weight:600}}
  .spark{{font-family:Georgia,serif;font-style:italic;font-size:15px;opacity:.94;max-width:34ch}}
  .spark.tierc{{color:var(--dim);font-size:14px}}.spark.tierc small{{font-style:normal;font-size:11px}}
  .snips{{display:flex;gap:6px;flex-wrap:wrap;margin-top:2px;padding:0 12px}}
  .chip{{border:1px solid #ffffff2b;background:#ffffff12;color:var(--ink);
    min-height:44px;padding:9px 14px;border-radius:999px;font:600 13.5px/1 inherit;display:inline-flex;align-items:center;gap:7px}}
  .chip:active{{transform:scale(.97)}}
  .chip.snip{{min-height:38px;padding:7px 12px;font-size:12.5px}}
  .chip.snip i{{font-style:normal;color:var(--glow)}}
  .chip.free{{border-color:#7BE0AD55;color:var(--mint)}}
  .chip.genre b{{color:var(--glow);font-weight:700}}
  .z-venue{{display:block;border-top:1px solid #ffffff1c;margin:6px 0 0;background:#ffffff0a;border-radius:14px;overflow:hidden}}
  .vphoto{{position:relative;height:clamp(60px,8dvh,92px)}}
  .vphoto svg{{width:100%;height:100%;display:block}}
  .vphoto .go{{top:8px;background:#000000a8;padding:4px 10px;border-radius:999px}}
  .vlink{{display:block}}
  .vlink:active{{background:#ffffff10}}
  .vrow{{display:flex;align-items:center;gap:10px;padding:8px 12px 6px}}
  .vtext{{display:flex;flex-direction:column;gap:1px;min-width:0}}
  .vname{{font-weight:700;font-size:16px}}
  .vchar{{color:var(--dim);font-size:13px;font-style:italic}}
  .vmeta{{font-size:12.5px;color:var(--glow)}}
  .vfoot{{display:flex;align-items:center;gap:8px;padding:0 12px 10px;flex-wrap:wrap}}
  .vspecial{{flex:1;min-width:170px;font-size:12.5px;color:var(--mint);border:1px dashed #7BE0AD44;border-radius:10px;padding:7px 10px}}
  .vspecial small{{display:block;color:var(--dim);font-size:10px;letter-spacing:.06em;text-transform:uppercase}}
  .vnearby{{border:1px solid #ffffff2b;background:#ffffff12;min-height:40px;padding:10px 13px;border-radius:999px;font:600 12.5px/1 inherit;display:inline-flex;align-items:center}}
  .vsite{{font-size:12.5px;color:var(--glow);text-decoration:underline;text-underline-offset:2px}}
  .minimap{{flex:none;width:48px;height:52px;border-radius:10px;background:#ffffff10;display:grid;place-items:center}}
  .minimap svg{{width:40px;height:46px}}
  .minimap .austin-shape{{fill:#ffffff14;stroke-width:1.4}}
  .minimap .austin-river{{stroke-width:1.6}}
  .rail{{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;align-items:center;padding:0 12px 2px}}
  .lens{{position:fixed;inset:0;z-index:20;background:#000000f6;display:none;flex-direction:column;
    padding:calc(var(--safe-t) + 60px) 20px calc(var(--safe-b) + 20px);overflow-y:auto}}
  .lens:target{{display:flex}}
  .lens .who{{font-family:Georgia,serif;font-size:clamp(24px,6.6vw,32px);margin-bottom:4px}}
  .lens .ph{{flex:none;height:clamp(100px,16dvh,160px);margin-bottom:12px}}
  .lens dl{{margin:10px 0 14px;display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:15px}}
  .lens dt{{color:var(--dim)}} .lens dd a{{color:var(--glow)}}
  .lens .back{{position:fixed;top:calc(var(--safe-t) + 12px);left:14px;z-index:2}}
  .lens .switch{{position:fixed;top:calc(var(--safe-t) + 12px);right:14px;z-index:2}}
  .lens .mapline{{display:flex;align-items:center;gap:12px}}
  .lens .mapline .minimap{{width:60px;height:66px}}.lens .mapline .minimap svg{{width:50px;height:58px}}
  .lens .snips{{padding:0}}
  .gcard{{display:flex;align-items:baseline;gap:10px;border:1px solid #ffffff22;background:#ffffff0d;border-radius:14px;padding:12px 14px;margin-top:8px}}
  .gcard:active{{background:#ffffff1a}}
  .gcard .gwho{{font-family:Georgia,serif;font-size:17px}}
  .gcard .gmeta{{margin-left:auto;text-align:right;font-size:12.5px;color:var(--dim);white-space:nowrap}}
  .gcard .gmeta b{{color:var(--glow);font-weight:600}}
  .gcard.gone{{opacity:.45}}
  .nearmap{{position:relative;border-radius:14px;overflow:hidden;background:#101018;margin-bottom:10px}}
  .nearmap svg{{width:100%;height:auto;display:block}}
  .near-street{{stroke:#ffffff18;stroke-width:1.6;fill:none}}
  .near-ring{{fill:none;stroke:#7BE0AD44;stroke-dasharray:2 2}}
  .near-label{{fill:#BDB5A6;font:5px "Space Grotesk",system-ui,sans-serif;letter-spacing:.05em}}
  .near-venue{{fill:var(--ember)}}
  .near-spot{{fill:var(--glow)}}
  .ncard{{display:flex;align-items:baseline;gap:10px;border:1px solid #ffffff22;background:#ffffff0d;border-radius:12px;padding:10px 13px;margin-top:7px}}
  .ncard .nwho{{font-weight:700}}
  .ncard .ntype{{color:var(--dim);font-size:12px;font-style:italic}}
  .ncard .nhow{{margin-left:auto;text-align:right;font-size:12px;color:var(--mint);white-space:nowrap}}
  .gnote{{font-size:12px;color:var(--dim);margin-top:10px}}
  .fixnote{{font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);margin:0 0 8px}}
  .gcard{{flex-wrap:wrap}}
  .gwhy{{flex-basis:100%;font-size:12px;color:var(--mint);margin-top:3px}}
  .gwhy em{{color:var(--dim);font-style:italic}}
  .desires{{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}}
  .memory{{border:1px dashed #7BE0AD44;border-radius:12px;padding:10px 12px;font-size:13px;color:var(--mint);margin-top:8px}}
  .memory small{{display:block;color:var(--dim);font-size:10px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:3px}}
  .askfab{{position:fixed;right:14px;bottom:calc(var(--safe-b) + 14px);z-index:8;border:1px solid #ffffff2b;background:#15151df0;
    color:var(--ink);min-height:48px;padding:12px 16px;border-radius:999px;font:600 13.5px/1 "Space Grotesk",system-ui,sans-serif;
    display:inline-flex;align-items:center;gap:8px;box-shadow:0 4px 18px #00000080}}
  details.unc{{display:inline-block;margin-left:auto}}
  details.unc summary{{list-style:none;cursor:pointer;min-width:44px;min-height:44px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;color:var(--dim);border:1px dashed #ffffff2b}}
  details.unc summary::-webkit-details-marker{{display:none}}
  details.unc .sheet{{position:fixed;left:14px;right:14px;bottom:calc(var(--safe-b) + 14px);background:var(--night2);border:1px solid #ffffff22;border-radius:16px;padding:16px;z-index:30;font-size:14px}}
  .sheet a{{color:var(--glow)}} .sheet em{{color:var(--dim);font-size:12px}}
  .fin{{min-height:40dvh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:6px}}
  .fin h2{{font-family:Georgia,serif;font-size:clamp(22px,6vw,28px)}}
  .fin p{{color:var(--dim);font-size:14px}}
  @media (prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}
</style>
</head>
<body>
<header class="masthead"><h1>Tonight in Austin</h1><span class="now" id="nowlabel"></span></header>

<section class="sky" id="sky">
  <h2>Tonight: {len(SHOWS)} shows, {venue_count} rooms.</h2>
  <p class="sub">Tap a part of town or a genre — or scroll for all of tonight, by start time.</p>
  <p class="sub" style="font-size:11px">Prototype — every listing and detail on this page is sample data.</p>
  <div class="citymap" role="group" aria-label="Austin, by part of town">
    <svg viewBox="0 0 44 50">
      <path class="austin-shape" d="M17 2l9 1 4 5 8 3-1 8 5 6-6 8 1 9-8 5-9-1-6-6 1-8-6-6 3-8-2-6z"/>
      <path class="austin-river" d="M2 20q10 3 16 7t24 9"/>
      {sky_parts}
    </svg>
  </div>
  <div class="constellation" role="group" aria-label="Genres playing tonight">{sky_chips}</div>
  <div class="rail" style="justify-content:center;padding:0">
    <a class="chip" href="#ask"><svg class="glyph" viewBox="0 0 20 20"><path d="M10 2a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3zm-5 8a5 5 0 0 0 10 0h1.6a6.6 6.6 0 0 1-5.8 6.55V19H8.2v-2.45A6.6 6.6 0 0 1 3.4 10z" fill="currentColor"/></svg>Tell me what you're interested in</a>
    <a class="chip" href="#{ordered[0]["id"]}">All shows ↓</a>
  </div>
</section>
{cards_html}
<section class="fin" id="fin">
  <h2>End of tonight's list.</h2>
  <p id="finline">{len(SHOWS)} shows listed above, by start time.</p>
  <p>Prototype fixture data: every artist and listing is fictional; venues are real Austin rooms used as setting. Venue details (addresses, distances, character lines), specials, provenance panels, and all nearby guidance are illustrative samples of the layout — not verified facts about these businesses. In the product, every one of these comes from a sourced, freshness-stamped pipeline.</p>
  <div class="rail" style="justify-content:center">
    <a class="chip" href="#sky">↑ Top</a>
  </div>
</section>
<a class="askfab" href="#ask" aria-label="Ask for tonight"><svg class="glyph" viewBox="0 0 20 20"><path d="M10 2a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3zm-5 8a5 5 0 0 0 10 0h1.6a6.6 6.6 0 0 1-5.8 6.55V19H8.2v-2.45A6.6 6.6 0 0 1 3.4 10z" fill="currentColor"/></svg>Ask</a>
{lenses_html}
<script>
// Progressive enhancement only — the page is complete without this.
// In a JS-capable browser: hide ended shows, tag live ones, stamp the clock.
(function(){{
  try{{
    var SET=120, now=new Date(), nm=now.getHours()*60+now.getMinutes(); if(nm<300)nm+=1440;
    var q=new URLSearchParams(location.search).get('at');
    if(q){{var p=q.split(':');nm=(+p[0]<5?+p[0]+24:+p[0])*60+(+p[1]||0)}}
    var pm=function(t){{var p=t.split(':');var h=+p[0];if(h<5)h+=24;return h*60+(+p[1])}};
    var gone=0;
    document.querySelectorAll('[data-start]').forEach(function(el){{
      var s=pm(el.dataset.start);
      if(s+SET<nm){{el.classList.add('gone');if(el.classList.contains('room'))gone++;}}
      else if(s<=nm){{var t=el.querySelector('.livetag');if(t)t.textContent=' · on now';}}
    }});
    var lbl=document.getElementById('nowlabel');
    if(lbl){{var h=Math.floor(nm/60)%24,m=nm%60,ap=h>=12?'PM':'AM';lbl.textContent='now '+((h%12)||12)+':'+String(m).padStart(2,'0')+' '+ap;}}
    if(gone){{var f=document.getElementById('finline');
      f.textContent=gone+' earlier show'+(gone>1?'s':'')+' ended and are hidden. '+({len(SHOWS)}-gone)+' listed above, by start time.';}}
  }}catch(e){{console.error('flow clock enhancement failed (page remains complete without it):',e)}}
}})();
// Voice enhancement (founder round 9): browser speech recognition mapped
// onto the SAME pre-computed desire lenses the chips reach by touch —
// voice adds an input mode, never a different answer. Hidden when the
// browser has no recognizer; failures log loudly.
(function(){{
  try{{
    var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    var mic=document.getElementById('micbtn'), note=document.getElementById('voicenote'), heard=document.getElementById('heard');
    if(!mic)return;
    if(!SR){{return}}
    mic.hidden=false; note.textContent='Tap Speak it, allow the mic, and say what you feel like — or use the chips.';
    mic.addEventListener('click',function(){{
      var r=new SR(); r.lang='en-US'; r.maxAlternatives=1;
      heard.textContent='listening…';
      r.onresult=function(ev){{
        var t=ev.results[0][0].transcript;
        heard.textContent='heard: “'+t+'”';
        var s=t.toLowerCase();
        var dest=/free/.test(s)?'#ask-free'
          :/danc|two.?step|cumbia|move/.test(s)?'#ask-dance'
          :/quiet|chill|candle|jazz|listen|date/.test(s)?'#ask-quiet'
          :/dinner|food|eat|taco|bbq|kitchen|menu/.test(s)?'#ask-dinner'
          :/outside|outdoor|patio|open.?air|backyard/.test(s)?'#ask-outdoors'
          :/late|midnight|after.?hours/.test(s)?'#ask-late'
          :/new|never been|somewhere else|different/.test(s)?'#ask-new'
          :/cheap|close|near|walk/.test(s)?'#ask-cheapclose'
          :/loud|heavy|punk|wall|rock|guitar/.test(s)?'#ask-loud':null;
        if(dest)location.hash=dest;
        else heard.textContent+=' — no match yet in this prototype; try a chip below.';
      }};
      r.onerror=function(e){{heard.textContent='voice error: '+e.error+' — the chips below do the same thing.';console.error('voice recognition:',e.error)}};
      r.start();
    }});
  }}catch(e){{console.error('voice enhancement failed (chips remain fully functional):',e)}}
}})();
</script>
</body>
</html>
'''

OUT.write_text(page)
print(f"wrote {OUT} ({len(page):,} bytes)")
