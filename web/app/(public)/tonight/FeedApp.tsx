"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { domainHue, domainLabel } from "../../../lib/domains";
import { trustDisplay } from "../../../lib/trust";
import {
  detailMapUrl as mapUrl,
  detailPrice as fmtPrice,
  detailProviderLabel,
  detailTrustKind,
  detailWhen,
  eventHref,
  httpOrNull as httpUrl,
  statusNote,
  telHref,
  venueWebsite,
} from "../../../lib/detail";
import { contextualPreview } from "../../../lib/preview";
import Link from "next/link";
import type { LicensedEvent, SparkLine } from "../../../lib/licensed";
import {
  filtersToQuery,
  isLensHistoryState,
  lensHistoryState,
  queryToFilters,
  externalAriaLabel,
  handoffCaption,
} from "../../../lib/nav";
import {
  DESIRES,
  DESIRE_BY_KEY,
  applyDesire,
  applyFilters,
  bucketByDate,
  buildPlan,
  dayTabs,
  facet,
  genreFacet,
  groupByDomain,
  liveEvents,
  type PlanScope,
} from "../../../lib/feed";

// ── presentational helpers ───────────────────────────────────────────────────
const TZ = "America/Chicago";

function fmtWhen(iso: string | null): string {
  if (!iso) return "Date TBA";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Date TBA";
  return d.toLocaleString("en-US", { timeZone: TZ, weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
function fmtTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit" });
}
// Date only (no time) — for the far-out "Beyond" rows, where the exact minute
// months away is noise; the day is what's scannable.
function fmtDate(iso: string | null): string {
  if (!iso) return "Date TBA";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Date TBA";
  return d.toLocaleDateString("en-US", { timeZone: TZ, weekday: "short", month: "short", day: "numeric" });
}
function focusLine(e: LicensedEvent): string {
  const parts = [domainLabel(e.category), e.subsegment].filter(Boolean) as string[];
  return parts.filter((v, i) => parts.indexOf(v) === i).join(" · ");
}
function headline(e: LicensedEvent): string {
  return e.performer && e.performer.length <= 80 ? e.performer : e.title;
}

// The Spark Line — the card's primary curiosity gap (UI Canon §4). tier C is
// AI-drafted and carries a quiet ✳; tapping the line opens the canon's
// one-tap-dismiss disclosure sheet ("Drafted from [artist]'s own materials." —
// founder-shortened 2026-08-04) — the same native <details> pattern as
// the detail page's uncertainty disclosure: one tap in, one tap gone, no modal,
// no history entry. tier B credits its critic. Display only — never ranks or
// filters, and absent when there is no approved line (an honest gap).
// Exported for tests.
export function SparkLineView({ spark, artist }: { spark?: SparkLine | null; artist: string }) {
  if (!spark || !spark.text) return null;
  const aiDrafted = spark.tier === "C";
  if (!aiDrafted) {
    return (
      <span className="spark">
        <span className="sparktext">{spark.text}</span>
        {spark.attribution ? <span className="sparkattr"> — {spark.attribution}</span> : null}
      </span>
    );
  }
  return (
    <details className="spark ai sparkdisc">
      <summary aria-label={`${spark.text} — AI-drafted line, tap for what that means`}>
        <span className="sparktext">{spark.text}</span>
        <span className="sparkmark" aria-hidden="true">{" ✳"}</span>
        {spark.attribution ? <span className="sparkattr"> — {spark.attribution}</span> : null}
      </summary>
      <span className="sparksheet" role="note">
        Drafted from {artist}&rsquo;s own materials.
      </span>
    </details>
  );
}

// Provenance-accurate trust display. Licensed rows are stated by an
// authoritative ticketing source; a "promoted" row was gated and published from
// a venue/organizer listing — so it gets honest "listing" wording. Provider
// wording + trust KIND live in lib/detail.ts so the card, the lens, and the
// detail page cannot drift into different claims about the same row.
function trustFor(e: LicensedEvent) {
  return trustDisplay(e.confidence, detailProviderLabel(e), detailTrustKind(e));
}

function TrustMark({ e }: { e: LicensedEvent }) {
  const t = trustFor(e);
  if (!t.surface || !t.marker) return null;
  return <span className={`cau${t.disputed ? " disp" : ""}`} title={t.sheet}>{t.marker}</span>;
}

// ── the two-door card (a "room"): a spare hook at rest; depth lives in the
// slide-out lenses (design canon §2/§6 — progressive disclosure, calm over
// clutter). The artist zone and the venue zone are coequal tappable doors, each
// opening its own lens; the card itself carries only what earns a glance:
// time · price · on-now · the quiet uncertainty mark, then the two doors. ──────
type LensSide = "artist" | "venue";

function RichCard({ e, onNow, onOpen }: {
  e: LicensedEvent; onNow: boolean; onOpen: (e: LicensedEvent, side: LensSide) => void;
}) {
  const price = fmtPrice(e);
  const img = httpUrl(e.image_url);
  const focus = focusLine(e);
  // The card's curiosity hook — a type-aware preview affordance ("Hear them",
  // "Watch a talk", "See a set"). It is honest-by-construction (lib/preview.ts:
  // a name search on a service the user already uses, never a claim a result
  // "is" them) and returns null for a type we can't preview — an honest gap, no
  // filler. Tapping the artist door opens the lens where the actual links live,
  // so the card stays spare (design canon §2/§6) while gaining a real hook.
  const preview = contextualPreview(e);
  return (
    <article className="room">
      {img
        ? <div className="rph" style={{ backgroundImage: `url(${img})` }} aria-hidden />
        : (
          // No image: give the card a real labeled cover (domain-hued) rather
          // than a 6px sliver, so image-less events read as finished cards and
          // the grid stays visually even. Decorative — the domain also shows in
          // the focus line below — so it is aria-hidden.
          <div className="rnoph" aria-hidden
            style={{ background: `linear-gradient(125deg, hsl(${domainHue(e.category)} 55% 24%), hsl(${(domainHue(e.category) + 40) % 360} 48% 15%))` }}>
            <span className="rnophlabel">{domainLabel(e.category)}</span>
          </div>
        )}
      <div className="rbody">
        <div className="rtime">
          <span className="when">{fmtWhen(e.start_time)}</span>
          {onNow ? <span className="onnow">on now</span> : null}
          <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
          <TrustMark e={e} />
        </div>
        {/* The artist door is an invisible full-zone overlay button rather than
            a wrapping <button>, because the tier-C Spark Line inside the zone is
            itself interactive (the §4 ✳ tap-to-dismiss disclosure) and
            interactive elements must never nest (axe: nested-interactive). The
            overlay keeps the whole zone tappable exactly as before; the
            disclosure sits above it (z-index) and wins only on its own row. */}
        <div className="zone z-artist">
          <button type="button" className="zdoor" onClick={() => onOpen(e, "artist")}
            aria-label={`${headline(e)}${e.spark ? ` — ${e.spark.text}` : ""} — open artist details${preview ? ` and ${preview.label.toLowerCase()}` : ""}`} />
          <span className="who">{headline(e)}</span>
          {focus ? <span className="focus">{focus}</span> : null}
          {/* Canon §2 artist-zone order: Spark Line (the primary curiosity gap,
              §4) sits above the smaller contextual-preview cue (§3). Both are
              canonical card elements; the preview stays a spare affordance
              ("▸ Hear them"), not a second summary, so §1 calm-over-clutter holds. */}
          <SparkLineView spark={e.spark} artist={headline(e)} />
          {preview ? <span className="hook">{preview.label}</span> : null}
          <span className="go" aria-hidden="true">artist ›</span>
        </div>
        <button type="button" className="zone z-venue" onClick={() => onOpen(e, "venue")}
          aria-label={`${e.venue_name ?? "Venue"} — open venue details`}>
          <span className="vname">{e.venue_name}{e.venue_area ? <span className="varea"> · {e.venue_area}</span> : null}</span>
          <span className="go" aria-hidden="true">venue ›</span>
        </button>
      </div>
    </article>
  );
}

// ── the lens: a slide-out sheet that reveals depth WITHOUT leaving the feed
// (design canon §6). A switch flips artist↔venue in either order; Escape and the
// backdrop close it; the sheet takes focus on open. Everything it shows is data
// we already hold — no fabrication, honest gaps where a field is absent. ───────
function Lens({ e, side, onNow, onSide, onClose }: {
  e: LicensedEvent; side: LensSide; onNow: boolean;
  onSide: (s: LensSide) => void; onClose: () => void;
}) {
  const sheetRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    sheetRef.current?.focus();
    // Escape closes; Tab is trapped inside the sheet so keyboard focus can never
    // wander to the (inert) feed behind the modal (evaluator #130 a11y note).
    function onKey(ev: KeyboardEvent) {
      if (ev.key === "Escape") { onClose(); return; }
      if (ev.key !== "Tab") return;
      const root = sheetRef.current;
      if (!root) return;
      const f = Array.from(
        root.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'),
      );
      if (f.length === 0) return;
      const first = f[0];
      const last = f[f.length - 1];
      const active = document.activeElement;
      if (active && !root.contains(active)) { ev.preventDefault(); first.focus(); return; }
      if (ev.shiftKey && active === first) { ev.preventDefault(); last.focus(); }
      else if (!ev.shiftKey && active === last) { ev.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", onKey);
    document.body.classList.add("lens-open");
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("lens-open");
    };
  }, [onClose]);

  const price = fmtPrice(e);
  const tix = httpUrl(e.ticket_url);
  const map = mapUrl(e);
  const site = venueWebsite(e.venue_url);
  const tel = telHref(e.venue_phone);
  const sub = trustFor(e);
  const preview = contextualPreview(e);
  const status = statusNote(e);
  const secondary = headline(e) !== e.title ? e.title : null;

  return (
    <div className="lensroot">
      <div className="lensbg" onClick={onClose} aria-hidden="true" />
      <div className="lenswrap">
        <div className="sheet" role="dialog" aria-modal="true" aria-label={`${headline(e)} at ${e.venue_name ?? "venue"}`}
          tabIndex={-1} ref={sheetRef}>
          <div className="lhead">
            <div className="lswitch" role="tablist" aria-label="Artist or venue">
              <button type="button" role="tab" aria-selected={side === "artist"} className={side === "artist" ? "on" : ""} onClick={() => onSide("artist")}>Artist</button>
              <button type="button" role="tab" aria-selected={side === "venue"} className={side === "venue" ? "on" : ""} onClick={() => onSide("venue")}>Venue</button>
            </div>
            {/* Trust marker lives in the header so it shows on BOTH tabs — the
                modal covers the card's own marker, and a disputed/unverified
                event's trust state must never be hidden behind the venue tab
                (evaluator #130, absence-only lens: disputed shown-never-hidden). */}
            <span className="lhtrust"><TrustMark e={e} /></span>
            <button type="button" className="lclose" onClick={onClose} aria-label="Close">×</button>
          </div>

          <div className="lbody">
            {side === "artist" ? (
              <>
                <p className="lwhen2">{detailWhen(e)}{onNow ? <span className="onnow">on now</span> : null}</p>
                <h3 className="lti2">{headline(e)}</h3>
                {secondary ? <p className="lsub2">{secondary}</p> : null}
                {focusLine(e) ? <p className="lfocus">{focusLine(e)}</p> : null}
                {/* The Spark Line rides into the lens (canon §2 order: after the
                    act, before logistics) with the same §4 ✳ disclosure — the
                    lens is the artist's expanded room, and the line's honest
                    mark travels with it wherever it renders. */}
                <SparkLineView spark={e.spark} artist={headline(e)} />
                {status ? <p className="lstatus">{status}</p> : null}
                <div className="lact">
                  <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
                  {/* TERMINAL handoff (nav canon §8): tickets finish on the
                      partner's site — same-tab (never a gratuitous new tab on
                      mobile; Back returns here), honestly labeled with where
                      it finishes, announced to screen readers. */}
                  {tix ? (
                    <a className="lbtn" href={tix} aria-label={externalAriaLabel("Get tickets", tix)}>
                      Get tickets ↗{handoffCaption(tix) ? <span className="lhand"> · {handoffCaption(tix)}</span> : null}
                    </a>
                  ) : null}
                </div>
                {preview ? (
                  <div className="llisten">
                    <span className="llbl">{preview.label}</span>
                    {/* REFERENCE links (§8): a listen search is something a
                        person keeps open while deciding — the sanctioned
                        new-tab case, labeled for screen readers. */}
                    {preview.links.map((l) => (
                      <a key={l.service} className="lchip" href={l.url} target="_blank" rel="noopener noreferrer"
                        aria-label={externalAriaLabel(`${preview.label} on ${l.service}`, l.url)}>{l.service} ↗</a>
                    ))}
                  </div>
                ) : null}
              </>
            ) : (
              <>
                <h3 className="lti2">{e.venue_name ?? "Venue"}</h3>
                {(e.venue_area || e.venue_city) ? (
                  <p className="lsub2">{[e.venue_area, e.venue_city].filter(Boolean).join(" · ")}</p>
                ) : null}
                {map ? (
                  <a className="laddr" href={map} target="_blank" rel="noopener noreferrer"
                    aria-label={externalAriaLabel("Open the address in maps", map)}>{e.venue_address ? `${e.venue_address} ↗` : "Open in maps ↗"}</a>
                ) : null}
                <div className="lact">
                  {tel ? <a className="lbtn" href={tel}>Call the venue</a> : null}
                  {site ? (
                    <a className="lbtn" href={site} target="_blank" rel="noopener noreferrer"
                      aria-label={externalAriaLabel("Venue website", site)}>Venue website ↗</a>
                  ) : null}
                </div>
                {!e.venue_address && !tel && !site ? (
                  <p className="lgap">We only have this venue&rsquo;s name and area so far — more venue detail is on the way.</p>
                ) : null}
              </>
            )}

            {/* Provenance shown on EVERY tab — trust display is a property of the
                event, not of the door you came through. */}
            <div className="lknow">
              <span className="llbl">How we know</span>
              <p>{sub.sheet}</p>
            </div>
            <Link className="lfull" href={eventHref(e)}>Open full page ↗</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function CondensedRow({ e, onNow }: { e: LicensedEvent; onNow: boolean }) {
  const price = fmtPrice(e);
  return (
    <div className="row">
      <span className="when">{fmtWhen(e.start_time)}{onNow ? <span className="onnow">on now</span> : null}</span>
      <span className="bd2">
        <span className="ti"><Link className="tilink" href={eventHref(e)}>{headline(e)}</Link><TrustMark e={e} /></span><br />
        <span className="mt">{focusLine(e)} · {e.venue_name}{e.venue_area ? ` · ${e.venue_area}` : ""}</span>
      </span>
      <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
    </div>
  );
}

// The tersest tier — one scannable line for far-out events: date · act · venue ·
// price. Trust marker still rides along (never dropped, even here).
function LineRow({ e }: { e: LicensedEvent }) {
  const price = fmtPrice(e);
  return (
    <div className="lrow">
      <span className="lwhen">{fmtDate(e.start_time)}</span>
      <span className="lti">
        <Link className="tilink" href={eventHref(e)}>{headline(e)}</Link>
        <TrustMark e={e} />
      </span>
      <span className="lven">{e.venue_name}{e.venue_area ? ` · ${e.venue_area}` : ""}</span>
      <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
    </div>
  );
}

// ── chip row helper ──────────────────────────────────────────────────────────
function toggle(set: Set<string>, v: string): Set<string> {
  const n = new Set(set);
  n.has(v) ? n.delete(v) : n.add(v);
  return n;
}

export default function FeedApp({ events, serverNowMs, qaFrozenClock }: {
  events: LicensedEvent[]; serverNowMs: number;
  // QA fixture mode only (web/qa/fixtures.ts): keep the server's frozen clock
  // after mount so screenshots are deterministic. Never set in production —
  // the real feed must always re-read the phone's real clock (canon §9).
  qaFrozenClock?: boolean;
}) {
  const [nowMs, setNowMs] = useState(serverNowMs);
  const [mounted, setMounted] = useState(false);
  const [tabKey, setTabKey] = useState("all");
  const [domains, setDomains] = useState<Set<string>>(new Set());
  const [areas, setAreas] = useState<Set<string>>(new Set());
  const [genres, setGenres] = useState<Set<string>>(new Set());
  const [freeOnly, setFreeOnly] = useState(false);
  const [desire, setDesire] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanScope | null>(null);
  const [mode, setMode] = useState<"browse" | "ask" | "plan">("browse");
  // The open lens: which event, and which door (artist/venue). null = closed.
  const [lens, setLens] = useState<{ id: string; side: LensSide } | null>(null);

  useEffect(() => {
    if (!qaFrozenClock) setNowMs(Date.now());
    // Filters live in the URL (nav canon §6): a shared/refreshed
    // ?when=…&domain=…&genre=… link reproduces the filtered feed. Applied
    // after mount (same pattern as the clock) so SSR stays deterministic.
    const f = queryToFilters(window.location.search);
    if (f.tabKey !== "all") setTabKey(f.tabKey);
    if (f.domains.size) setDomains(f.domains);
    if (f.areas.size) setAreas(f.areas);
    if (f.genres.size) setGenres(f.genres);
    if (f.freeOnly) setFreeOnly(true);
    setMounted(true);
  }, [qaFrozenClock]);

  // Keep the URL in step with the filters — replaceState, not pushState, so
  // Back stays a step UP (close lens / leave page), never an undo-tour of
  // every chip tap (nav canon §7: Back is a strict "undo my last step").
  useEffect(() => {
    if (!mounted) return;
    // Never rewrite the URL while the lens owns it (its entry carries the
    // event's own /tonight/<id> address).
    if (isLensHistoryState(window.history.state)) return;
    const q = filtersToQuery({ tabKey, domains, areas, genres, freeOnly });
    const next = `${window.location.pathname}${q}`;
    if (`${window.location.pathname}${window.location.search}` !== next) {
      window.history.replaceState(window.history.state, "", next);
    }
  }, [mounted, tabKey, domains, areas, genres, freeOnly]);

  // History-modeled lens (nav canon §6/§7): opening pushes a history entry AT
  // THE EVENT'S OWN URL, so (a) hardware/gesture Back closes the sheet before
  // it ever leaves the feed — the feed behind it is untouched, nothing to
  // restore — and (b) the address bar shows a shareable /tonight/<id> that
  // hard-loads as the full standalone page. popstate is the single source of
  // truth for closing; the UI's own close calls history.back() so the stack
  // never desyncs.
  useEffect(() => {
    function onPop() {
      if (!isLensHistoryState(window.history.state)) setLens(null);
    }
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // Base = the honest set minus only what has ENDED (a time filter, never a
  // confidence filter). Before mount we keep everything (deterministic SSR).
  const base = useMemo(() => (mounted ? liveEvents(events, nowMs) : events), [events, nowMs, mounted]);
  const tabs = useMemo(() => dayTabs(nowMs, 7), [nowMs]);
  const tab = tabs.find((t) => t.key === tabKey) ?? tabs[0];

  const areaFacet = useMemo(() => facet(base, "venue_area").slice(0, 8), [base]);
  // Layer-0 genre rail: up to 12 canonical genres present in the live set.
  const genreRail = useMemo(() => genreFacet(base).slice(0, 12), [base]);
  const domainGroupsAll = useMemo(() => groupByDomain(base), [base]);

  const filtered = useMemo(
    () => applyFilters(base, { tab, domains, areas, genreIds: genres, freeOnly }),
    [base, tab, domains, areas, genres, freeOnly],
  );

  const total = base.length;
  const freeCount = base.filter((e) => e.is_free || e.price_min === 0).length;

  const isOnNow = (e: LicensedEvent) => mounted && eventOnNow(e, nowMs);
  const openLens = (e: LicensedEvent, side: LensSide) => {
    const id = e.licensed_event_id;
    if (isLensHistoryState(window.history.state)) {
      // Already inside a lens entry (switching events would be unusual, but
      // the stack must stay one-deep): replace, never push a second layer.
      window.history.replaceState(lensHistoryState(id, side), "", eventHref(e));
    } else {
      window.history.pushState(lensHistoryState(id, side), "", eventHref(e));
    }
    setLens({ id, side });
  };
  const closeLens = () => {
    // Back out through history when the lens owns the top entry, so UI-close
    // and hardware Back leave an identical stack (§13.4); otherwise (e.g. a
    // stale state after an external return) just close.
    if (isLensHistoryState(window.history.state)) window.history.back();
    else setLens(null);
  };
  const lensEvent = lens ? base.find((e) => e.licensed_event_id === lens.id) ?? events.find((e) => e.licensed_event_id === lens.id) ?? null : null;

  return (
    <main className="flow">
      <div className="wrap">
        <div className="mast">
          <h1>1LIVE · Tonight in Austin</h1>
          <p className="lede">Everything on in Central Texas, in one place — real events, real venues, real prices.</p>
          <div className="kpis">
            <div className="kpi"><div className="v">{total.toLocaleString()}</div><div className="l">happening & upcoming</div></div>
            <div className="kpi"><div className="v">{domainGroupsAll.length}</div><div className="l">cultural domains</div></div>
            {freeCount > 0 ? <div className="kpi"><div className="v">{freeCount}</div><div className="l">free to attend</div></div> : null}
          </div>
        </div>

        {/* mode switch */}
        <div className="modes">
          <button className={mode === "browse" ? "on" : ""} onClick={() => setMode("browse")}>Browse</button>
          <button className={mode === "ask" ? "on" : ""} onClick={() => setMode("ask")}>Tell us what you&rsquo;re into</button>
          <button className={mode === "plan" ? "on" : ""} onClick={() => setMode("plan")}>Plan a day / night / weekend</button>
        </div>

        {mode === "ask" ? (
          <AskPanel base={base} nowMs={nowMs} desire={desire} setDesire={setDesire} isOnNow={isOnNow} />
        ) : mode === "plan" ? (
          <PlanPanel base={base} nowMs={nowMs} plan={plan} setPlan={setPlan} />
        ) : (
          <>
            {/* date tabs */}
            <nav className="datetabs">
              {tabs.map((t) => (
                <button key={t.key} className={t.key === tabKey ? "on" : ""} onClick={() => setTabKey(t.key)}>{t.label}</button>
              ))}
            </nav>

            {/* filters */}
            <div className="filters">
              <div className="frow">
                {domainGroupsAll.map((g) => (
                  <button key={g.domain.id} className={`chip${domains.has(g.domain.id) ? " on" : ""}`} onClick={() => setDomains(toggle(domains, g.domain.id))}>
                    <span className="dot" style={{ background: `hsl(${g.domain.hue} 65% 55%)` }} />{g.domain.label}<span className="n">{g.items.length}</span>
                  </button>
                ))}
              </div>
              {/* Genre rail (Layer 0): the canonical genres present tonight,
                  derived from local inventory. A lens, never a gate. */}
              {genreRail.length > 1 ? (
                <div className="frow">
                  {genreRail.map((g) => (
                    <button key={g.id} className={`chip${genres.has(g.id) ? " on" : ""}`} onClick={() => setGenres(toggle(genres, g.id))}>
                      {g.label}<span className="n">{g.n}</span>
                    </button>
                  ))}
                </div>
              ) : null}
              {areaFacet.length > 1 || genres.size || domains.size ? (
                <div className="frow">
                  {areaFacet.map((a) => (
                    <button key={a.value} className={`chip area${areas.has(a.value) ? " on" : ""}`} onClick={() => setAreas(toggle(areas, a.value))}>
                      {a.value}<span className="n">{a.n}</span>
                    </button>
                  ))}
                  <button className={`chip${freeOnly ? " on" : ""}`} onClick={() => setFreeOnly(!freeOnly)}>Free only</button>
                  {(domains.size || areas.size || genres.size || freeOnly || tabKey !== "all") ? (
                    <button className="chip clear" onClick={() => { setDomains(new Set()); setAreas(new Set()); setGenres(new Set()); setFreeOnly(false); setTabKey("all"); }}>Clear</button>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div className="count">{filtered.length.toLocaleString()} shown · by start time · no pay-to-rank</div>

            <EventList events={filtered} nowMs={nowMs} isOnNow={isOnNow} onOpen={openLens} />
          </>
        )}

        <footer>
          Real, licensed listings from authoritative ticketing sources — never fabricated. Times and prices can change;
          each listing links to the venue/ticket source as the last word. Long-tail domains (libraries, lectures, readings,
          block parties) are being added from 1Live&rsquo;s own pipeline; what you see here is the ticketed spine.
        </footer>
      </div>

      {lens && lensEvent ? (
        <Lens
          e={lensEvent}
          side={lens.side}
          onNow={isOnNow(lensEvent)}
          onSide={(s) => {
            // The artist↔venue switch stays within the same history entry —
            // it is a view flip inside one layer, not a new place.
            window.history.replaceState(lensHistoryState(lens.id, s), "", window.location.href);
            setLens({ id: lens.id, side: s });
          }}
          onClose={closeLens}
        />
      ) : null}
    </main>
  );
}

function eventOnNow(e: LicensedEvent, nowMs: number): boolean {
  const start = e.start_time ? Date.parse(e.start_time) : NaN;
  if (Number.isNaN(start) || start > nowMs) return false;
  const end = e.end_time ? Date.parse(e.end_time) : NaN;
  const endMs = Number.isNaN(end) ? start + 3 * 3600_000 : end;
  return endMs > nowMs;
}

// The near-term "This week" bucket keeps the cultural-domain grouping (the
// categorization that helps most when there's a lot on), rendered as rich cards.
function RichBucket({ items, isOnNow, onOpen }: {
  items: LicensedEvent[]; isOnNow: (e: LicensedEvent) => boolean; onOpen: (e: LicensedEvent, side: LensSide) => void;
}) {
  const groups = groupByDomain(items);
  return (
    <>
      {groups.map(({ domain: d, items: dItems }) => (
        <div key={d.id} className="dgroup" id={d.id}>
          <div className="sec"><span className="dot" style={{ background: `hsl(${d.hue} 65% 55%)`, width: 12, height: 12 }} /><h3>{d.label}</h3><span className="n">{dItems.length}</span></div>
          <div className="grid">{dItems.map((e) => <RichCard key={e.licensed_event_id} e={e} onNow={isOnNow(e)} onOpen={onOpen} />)}</div>
        </div>
      ))}
    </>
  );
}

// The feed renders in THREE date buckets of descending density — This week
// (rich two-door cards, domain-grouped) · Later this month (compact rows) ·
// Beyond (terse lines) — so longer-dated events are scannable instead of a wall
// of tall cards. bucketByDate is sum-preserving, so nothing is dropped.
function EventList({ events, nowMs, isOnNow, onOpen }: {
  events: LicensedEvent[]; nowMs: number; isOnNow: (e: LicensedEvent) => boolean; onOpen: (e: LicensedEvent, side: LensSide) => void;
}) {
  const buckets = useMemo(() => bucketByDate(events, nowMs), [events, nowMs]);
  if (events.length === 0) return <div className="err">No events match — clear a filter or pick another day.</div>;
  return (
    <>
      {buckets.map((b) => (
        <section key={b.key} className={`bucket b-${b.key}`}>
          <div className="bhead">
            <h2>{b.label}</h2>
            <span className="bblurb">{b.blurb}</span>
            <span className="n">{b.items.length}</span>
          </div>
          {b.key === "rich" ? (
            <RichBucket items={b.items} isOnNow={isOnNow} onOpen={onOpen} />
          ) : b.key === "compact" ? (
            <div className="clist">{b.items.map((e) => <CondensedRow key={e.licensed_event_id} e={e} onNow={isOnNow(e)} />)}</div>
          ) : (
            <div className="llist">{b.items.map((e) => <LineRow key={e.licensed_event_id} e={e} />)}</div>
          )}
        </section>
      ))}
    </>
  );
}

function AskPanel({ base, nowMs, desire, setDesire, isOnNow }: {
  base: LicensedEvent[]; nowMs: number; desire: string | null; setDesire: (k: string | null) => void; isOnNow: (e: LicensedEvent) => boolean;
}) {
  const results = desire ? applyDesire(base, desire, nowMs) : [];
  const d = desire ? DESIRE_BY_KEY.get(desire) : null;
  return (
    <div className="ask">
      <h2 className="askh">What are you feeling?</h2>
      <p className="asksub">Tap what you&rsquo;re after — it&rsquo;s a lens, never a gate: the full night stays one tap away, and every match says why.</p>
      <div className="frow">
        {DESIRES.map((x) => (
          <button key={x.key} className={`chip big${desire === x.key ? " on" : ""}`} onClick={() => setDesire(desire === x.key ? null : x.key)}>{x.label}</button>
        ))}
      </div>
      {d ? (
        <>
          <div className="count">{results.length.toLocaleString()} match{results.length === 1 ? "" : "es"}, by start time{d.note ? ` — ${d.note}` : ""}</div>
          <div style={{ display: "grid", gap: 8 }}>
            {results.map((e) => (
              <div key={e.licensed_event_id} className="row">
                <span className="when">{fmtWhen(e.start_time)}{isOnNow(e) ? <span className="onnow">on now</span> : null}</span>
                <span className="bd2">
                  <span className="ti"><Link className="tilink" href={eventHref(e)}>{headline(e)}</Link><TrustMark e={e} /></span><br />
                  <span className="mt">{e.venue_name}{e.venue_area ? ` · ${e.venue_area}` : ""}</span><br />
                  <span className="why">why: {d.why(e)}</span>
                </span>
                <span className={`pr${fmtPrice(e).free ? " free" : ""}`}>{fmtPrice(e).text}</span>
              </div>
            ))}
            {results.length === 0 ? <div className="err">Nothing matches that right now — try another, or Browse the full list.</div> : null}
          </div>
        </>
      ) : (
        <p className="asknote">More ways to ask (dinner nearby, outdoor patios, walking distance) are coming as we add that data — we won&rsquo;t guess it.</p>
      )}
    </div>
  );
}

function PlanPanel({ base, nowMs, plan, setPlan }: {
  base: LicensedEvent[]; nowMs: number; plan: PlanScope | null; setPlan: (s: PlanScope | null) => void;
}) {
  const slots = plan ? buildPlan(base, plan, nowMs) : [];
  return (
    <div className="ask">
      <h2 className="askh">Build me a plan</h2>
      <p className="asksub">A suggestion assembled from tonight&rsquo;s real listings — clustered by neighborhood, one pick per time block. Every stop says why, and you can browse the full night anytime.</p>
      <div className="frow">
        {(["night", "day", "weekend"] as PlanScope[]).map((s) => (
          <button key={s} className={`chip big${plan === s ? " on" : ""}`} onClick={() => setPlan(plan === s ? null : s)}>A {s}</button>
        ))}
      </div>
      {plan ? (
        slots.length ? (
          <div className="plan">
            {slots.map((s, i) => (
              <div key={s.event.licensed_event_id} className="planslot">
                <div className="planblock">{s.block}</div>
                <div className="row">
                  <span className="when">{fmtTime(s.event.start_time)}</span>
                  <span className="bd2">
                    <span className="ti"><Link className="tilink" href={eventHref(s.event)}>{headline(s.event)}</Link></span><br />
                    <span className="mt">{s.event.venue_name}{s.event.venue_area ? ` · ${s.event.venue_area}` : ""}</span><br />
                    <span className="why">why: {s.why}</span>
                  </span>
                  <span className={`pr${fmtPrice(s.event).free ? " free" : ""}`}>{fmtPrice(s.event).text}</span>
                </div>
                {i < slots.length - 1 ? <div className="planarrow">then ↓</div> : null}
              </div>
            ))}
          </div>
        ) : <div className="err">Not enough upcoming events to build a {plan} right now — try Browse.</div>
      ) : null}
    </div>
  );
}
