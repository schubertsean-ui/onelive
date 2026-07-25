"use client";

import { useEffect, useMemo, useState } from "react";
import { domainHue, domainLabel, timeBand } from "../../../lib/domains";
import { trustDisplay } from "../../../lib/trust";
import type { LicensedEvent } from "../../../lib/licensed";
import {
  DESIRES,
  DESIRE_BY_KEY,
  applyDesire,
  applyFilters,
  buildPlan,
  dayTabs,
  facet,
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
function fmtPrice(e: LicensedEvent): { text: string; free: boolean; known: boolean } {
  if (e.is_free || e.price_min === 0) return { text: "Free", free: true, known: true };
  if (e.price_min != null && e.price_max != null && e.price_max !== e.price_min)
    return { text: `$${Math.round(e.price_min)}–$${Math.round(e.price_max)}`, free: false, known: true };
  if (e.price_min != null) return { text: `$${Math.round(e.price_min)}+`, free: false, known: true };
  return { text: "See tickets", free: false, known: false };
}
function httpUrl(u: string | null): string | null {
  if (!u) return null;
  try { const p = new URL(u).protocol; return p === "http:" || p === "https:" ? u : null; } catch { return null; }
}
function mapUrl(e: LicensedEvent): string | null {
  if (e.venue_lat != null && e.venue_lng != null) return `https://maps.apple.com/?q=${e.venue_lat},${e.venue_lng}`;
  const q = [e.venue_name, e.venue_address, e.venue_city].filter(Boolean).join(", ");
  return q ? `https://maps.apple.com/?q=${encodeURIComponent(q)}` : null;
}
function focusLine(e: LicensedEvent): string {
  const parts = [domainLabel(e.category), e.subsegment].filter(Boolean) as string[];
  return parts.filter((v, i) => parts.indexOf(v) === i).join(" · ");
}
function headline(e: LicensedEvent): string {
  return e.performer && e.performer.length <= 80 ? e.performer : e.title;
}

// Provenance-accurate trust display. Licensed rows are stated by an
// authoritative ticketing source (Ticketmaster/SeatGeek/Eventbrite); a
// "promoted" row was gated and published from a venue/organizer listing — so it
// gets the honest "listing" wording, never "ticketing source".
const _PROVIDER_LABEL: Record<string, string> = {
  ticketmaster: "Ticketmaster",
  seatgeek: "SeatGeek",
  eventbrite: "Eventbrite",
  promoted: "a local venue or organizer listing",
};
function trustFor(e: LicensedEvent) {
  const label = _PROVIDER_LABEL[e.source_provider] ?? e.source_provider;
  const kind = e.source_provider === "promoted" ? "listing" : "ticketing";
  return trustDisplay(e.confidence, label, kind);
}

function TrustMark({ e }: { e: LicensedEvent }) {
  const t = trustFor(e);
  if (!t.surface || !t.marker) return null;
  return <span className={`cau${t.disputed ? " disp" : ""}`} title={t.sheet}>{t.marker}</span>;
}

function RichCard({ e, onNow }: { e: LicensedEvent; onNow: boolean }) {
  const price = fmtPrice(e);
  const map = mapUrl(e);
  const img = httpUrl(e.image_url);
  const tix = httpUrl(e.ticket_url);
  const sub = trustFor(e);
  const secondaryTitle = headline(e) !== e.title ? e.title : null;
  return (
    <div className="card">
      {img ? <div className="ph" style={{ backgroundImage: `url(${img})` }} />
        : <div className="noph" style={{ background: `linear-gradient(90deg, hsl(${domainHue(e.category)} 60% 45%), hsl(${(domainHue(e.category) + 40) % 360} 55% 38%))` }} />}
      <div className="bd">
        <span className="when">
          {fmtWhen(e.start_time)}
          {onNow ? <span className="onnow">on now</span> : null}
          <TrustMark e={e} />
        </span>
        <span className="ti">{headline(e)}</span>
        {secondaryTitle ? <span className="subti">{secondaryTitle}</span> : null}
        <span className="focus">{focusLine(e)}</span>
        <span className="ven">
          {e.venue_name}
          {e.venue_area ? <span className="addr"> · {e.venue_area}</span> : null}
        </span>
        {e.venue_address && map ? (
          <a className="addrlink" href={map} target="_blank" rel="noopener noreferrer">{e.venue_address} ↗</a>
        ) : null}
        <div className="foot">
          <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
          {e.on_sale_status === "offsale" ? <span className="avail">off sale</span> : null}
          {tix ? <a className="tix" href={tix} target="_blank" rel="noopener noreferrer">tickets ↗</a> : null}
        </div>
        <details className="unc"><summary>How we know</summary><div className="sheet">{sub.sheet}</div></details>
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
        <span className="ti">{headline(e)}<TrustMark e={e} /></span><br />
        <span className="mt">{focusLine(e)} · {e.venue_name}{e.venue_area ? ` · ${e.venue_area}` : ""}</span>
      </span>
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

export default function FeedApp({ events, serverNowMs }: { events: LicensedEvent[]; serverNowMs: number }) {
  const [nowMs, setNowMs] = useState(serverNowMs);
  const [mounted, setMounted] = useState(false);
  const [tabKey, setTabKey] = useState("all");
  const [domains, setDomains] = useState<Set<string>>(new Set());
  const [areas, setAreas] = useState<Set<string>>(new Set());
  const [freeOnly, setFreeOnly] = useState(false);
  const [desire, setDesire] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanScope | null>(null);
  const [mode, setMode] = useState<"browse" | "ask" | "plan">("browse");

  useEffect(() => { setNowMs(Date.now()); setMounted(true); }, []);

  // Base = the honest set minus only what has ENDED (a time filter, never a
  // confidence filter). Before mount we keep everything (deterministic SSR).
  const base = useMemo(() => (mounted ? liveEvents(events, nowMs) : events), [events, nowMs, mounted]);
  const tabs = useMemo(() => dayTabs(nowMs, 7), [nowMs]);
  const tab = tabs.find((t) => t.key === tabKey) ?? tabs[0];

  const areaFacet = useMemo(() => facet(base, "venue_area").slice(0, 8), [base]);
  const domainGroupsAll = useMemo(() => groupByDomain(base), [base]);

  const filtered = useMemo(
    () => applyFilters(base, { tab, domains, areas, freeOnly }),
    [base, tab, domains, areas, freeOnly],
  );

  const total = base.length;
  const freeCount = base.filter((e) => e.is_free || e.price_min === 0).length;

  const isOnNow = (e: LicensedEvent) => mounted && eventOnNow(e, nowMs);

  return (
    <main className="flow">
      <div className="demobar">
        Real, licensed events for the CAPCOG area — live from Ticketmaster. Private preview.
      </div>
      <div className="wrap">
        <div className="mast">
          <h1>ONE LIVE · Tonight in Austin</h1>
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
              {areaFacet.length > 1 ? (
                <div className="frow">
                  {areaFacet.map((a) => (
                    <button key={a.value} className={`chip area${areas.has(a.value) ? " on" : ""}`} onClick={() => setAreas(toggle(areas, a.value))}>
                      {a.value}<span className="n">{a.n}</span>
                    </button>
                  ))}
                  <button className={`chip${freeOnly ? " on" : ""}`} onClick={() => setFreeOnly(!freeOnly)}>Free only</button>
                  {(domains.size || areas.size || freeOnly || tabKey !== "all") ? (
                    <button className="chip clear" onClick={() => { setDomains(new Set()); setAreas(new Set()); setFreeOnly(false); setTabKey("all"); }}>Clear</button>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div className="count">{filtered.length.toLocaleString()} shown · by start time · no pay-to-rank</div>

            <EventList events={filtered} nowMs={nowMs} isOnNow={isOnNow} />
          </>
        )}

        <footer>
          Real, licensed listings from authoritative ticketing sources — never fabricated. Times and prices can change;
          each listing links to the venue/ticket source as the last word. Long-tail domains (libraries, lectures, readings,
          block parties) are being added from OneLive&rsquo;s own pipeline; what you see here is the ticketed spine.
        </footer>
      </div>
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

function EventList({ events, nowMs, isOnNow }: { events: LicensedEvent[]; nowMs: number; isOnNow: (e: LicensedEvent) => boolean }) {
  const groups = useMemo(() => groupByDomain(events), [events]);
  if (events.length === 0) return <div className="err">No events match — clear a filter or pick another day.</div>;
  return (
    <>
      {groups.map(({ domain: d, items }) => {
        const rich = items.filter((e) => timeBand(e.start_time, nowMs) === "rich");
        const later = items.filter((e) => timeBand(e.start_time, nowMs) !== "rich");
        return (
          <section key={d.id} id={d.id}>
            <div className="sec"><span className="dot" style={{ background: `hsl(${d.hue} 65% 55%)`, width: 12, height: 12 }} /><h2>{d.label}</h2><span className="n">{items.length}</span></div>
            {rich.length ? <div className="grid">{rich.map((e) => <RichCard key={e.licensed_event_id} e={e} onNow={isOnNow(e)} />)}</div> : null}
            {later.length ? <div style={{ display: "grid", gap: 8, marginTop: rich.length ? 10 : 0 }}>{later.map((e) => <CondensedRow key={e.licensed_event_id} e={e} onNow={isOnNow(e)} />)}</div> : null}
          </section>
        );
      })}
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
                  <span className="ti">{headline(e)}<TrustMark e={e} /></span><br />
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
                    <span className="ti">{headline(s.event)}</span><br />
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
