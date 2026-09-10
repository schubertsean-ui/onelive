"use client";

import { useEffect, useMemo, useState } from "react";
import type { LicensedEvent } from "../../../lib/licensed";
import { applyRegionScope, type RegionScope } from "../../../lib/region";
import {
  applyFilters,
  dayTabs,
  eventTiming,
  groupByDomain,
  liveEvents,
  viewCounts,
} from "../../../lib/feed";
import { byClock } from "../../../lib/dayClock";
import { applyTitleSlots } from "../../../lib/titleSlots";
import { detailPrice as fmtPrice, eventHref } from "../../../lib/detail";
import { FeedCard, SparkLineView, TrustMark } from "./FeedCard";
import type { LensSide } from "./TwoRoomCard";

export { SparkLineView };

function headline(e: LicensedEvent): string {
  return e.performer && e.performer.length <= 80 ? e.performer : e.title;
}

function toggle(set: Set<string>, v: string): Set<string> {
  const n = new Set(set);
  n.has(v) ? n.delete(v) : n.add(v);
  return n;
}

export function CondensedRow({ e, onNow, onOpen }: { e: LicensedEvent; onNow: boolean; onOpen: (e: LicensedEvent, side: LensSide) => void }) {
  const price = fmtPrice(e);
  return (
    <div className="row">
      <span className="when">{e.start_time ?? "Date TBA"}{onNow ? <span className="onnow">on now</span> : null}</span>
      <span className="bd2">
        <span className="ti"><button type="button" className="tilink" onClick={() => onOpen(e, "artist")}>{headline(e)}</button><TrustMark e={e} /></span>
      </span>
      <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
    </div>
  );
}

export function LineRow({ e, onOpen }: { e: LicensedEvent; onOpen: (e: LicensedEvent, side: LensSide) => void }) {
  const price = fmtPrice(e);
  return (
    <div className="lrow">
      <span className="lwhen">{e.start_time ?? "Date TBA"}</span>
      <span className="lti">
        <button type="button" className="tilink" onClick={() => onOpen(e, "artist")}>{headline(e)}</button>
        <TrustMark e={e} />
      </span>
      <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
    </div>
  );
}

export default function FeedLive({ events, serverNowMs, qaFrozenClock }: {
  events: LicensedEvent[];
  serverNowMs: number;
  qaFrozenClock?: boolean;
}) {
  const [nowMs, setNowMs] = useState(serverNowMs);
  const [mounted, setMounted] = useState(false);
  const [tabKey, setTabKey] = useState("today");
  const [region, setRegion] = useState<RegionScope>("capcog");
  const [domains, setDomains] = useState<Set<string>>(new Set());
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    if (!qaFrozenClock) setNowMs(Date.now());
    setMounted(true);
  }, [qaFrozenClock]);

  const printed = useMemo(() => events.map((e) => applyTitleSlots(e, nowMs)), [events, nowMs]);
  const live = useMemo(() => (mounted ? liveEvents(printed, nowMs) : printed), [printed, nowMs, mounted]);
  const tabs = useMemo(() => dayTabs(nowMs, 7), [nowMs]);
  const tab = tabs.find((t) => t.key === tabKey) ?? tabs[0];
  const base = useMemo(() => applyRegionScope(live, region), [live, region]);
  const domainGroupsAll = useMemo(() => groupByDomain(base), [base]);
  const filtered = useMemo(
    () => applyFilters(base, { tab, domains, areas: new Set(), genreIds: new Set(), freeOnly: false }),
    [base, tab, domains],
  );
  const counts = useMemo(() => viewCounts(live, filtered, tab, region), [live, filtered, tab, region]);
  const clock = useMemo(() => byClock(filtered), [filtered]);
  const isOnNow = (e: LicensedEvent) => {
    if (!mounted) return false;
    if (eventTiming(e, nowMs) !== "on-now") return false;
    if (!e.end_time) return false;
    const end = Date.parse(e.end_time);
    return Number.isFinite(end) && end > nowMs;
  };
  const onOpen = (e: LicensedEvent, _side: LensSide) => {
    window.location.href = eventHref(e);
  };
  const activeFilters = domains.size;

  return (
    <main className="flow">
      <div className="wrap">
        <div className="mast">
          <h1>1LIVE · Austin</h1>
          <p className="lede">What&rsquo;s on, by date. Earliest to latest.</p>
        </div>
        <nav className="datetabs">
          {tabs.map((t) => (
            <button key={t.key} className={t.key === tabKey ? "on" : ""} onClick={() => setTabKey(t.key)}>{t.label}</button>
          ))}
        </nav>
        <div className="fbar">
          <button type="button" className={`chip big fentry${filtersOpen || activeFilters ? " on" : ""}`}
            aria-expanded={filtersOpen} aria-controls="filterpanel"
            onClick={() => setFiltersOpen(!filtersOpen)}>
            Filters{activeFilters ? <span className="n">{activeFilters}</span> : null}
          </button>
          {activeFilters ? (
            <button className="chip clear" onClick={() => setDomains(new Set())}>Clear</button>
          ) : null}
        </div>
        {filtersOpen || activeFilters ? (
          <div className="filters fpanel" id="filterpanel">
            <div className="frow">
              {domainGroupsAll.map((g) => (
                <button key={g.domain.id} className={`chip${domains.has(g.domain.id) ? " on" : ""}`}
                  onClick={() => setDomains(toggle(domains, g.domain.id))}>
                  <span className="dot" style={{ background: `hsl(${g.domain.hue} 65% 55%)` }} />
                  {g.domain.label}<span className="n">{g.items.length}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="filters">
            <div className="frow">
              {domainGroupsAll.slice(0, 8).map((g) => (
                <button key={g.domain.id} className={`chip${domains.has(g.domain.id) ? " on" : ""}`}
                  onClick={() => setDomains(toggle(domains, g.domain.id))}>
                  {g.domain.label}<span className="n">{g.items.length}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="count">
          Showing {counts.shown.toLocaleString()} of {counts.windowTotal.toLocaleString()} known
          {" "}listing{counts.windowTotal === 1 ? "" : "s"} for {tab.key === "all" ? "everything upcoming" : tab.label}
          {" · earliest to latest"}
        </div>
        <p className="rnote">
          {region === "capcog" ? (
            <>
              <span>Scoped to the CAPCOG test region.</span>{" "}
              <button type="button" className="rlink" onClick={() => setRegion("everywhere")}>Show everywhere</button>
            </>
          ) : (
            <>
              <span>Region filter cleared — showing every place we hold.</span>{" "}
              <button type="button" className="rlink" onClick={() => setRegion("capcog")}>Back to the CAPCOG test region</button>
            </>
          )}
        </p>
        {filtered.length === 0 ? (
          <div className="err">No events match — pick another kind or day.</div>
        ) : (
          <>
            <div className="grid">
              {clock.timed.map((e) => (
                <FeedCard key={e.licensed_event_id} e={e} onNow={isOnNow(e)} onOpen={onOpen} />
              ))}
            </div>
            {clock.undated.length ? (
              <section className="bucket b-rich">
                <div className="bhead">
                  <h2>Date to be announced</h2>
                  <span className="n">{clock.undated.length}</span>
                </div>
                <div className="grid">
                  {clock.undated.map((e) => (
                    <FeedCard key={e.licensed_event_id} e={e} onNow={isOnNow(e)} onOpen={onOpen} />
                  ))}
                </div>
              </section>
            ) : null}
          </>
        )}
        <footer>
          Real listings from validated sources. Times and prices can change;
          each listing links to the venue/ticket source as the last word.
        </footer>
      </div>
    </main>
  );
}
