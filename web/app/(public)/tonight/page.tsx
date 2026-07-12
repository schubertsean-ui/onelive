"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchTonight } from "../../../lib/public-api";
import { TonightEvent } from "../../../lib/public-types";
import { formatDayLabel } from "../../../lib/time";
import { EventCard } from "../../../components/EventCard";
import { BrandMark } from "../../../components/BrandMark";
import { FeedSkeleton, FeedEmpty, FeedError } from "../../../components/FeedStates";

type Status = "loading" | "ready" | "error";

const CITY = "Austin";

// Small legend so the confidence vocabulary is explained up front, honestly.
const LEGEND: { tone: string; label: string }[] = [
  { tone: "confirmed", label: "Confirmed" },
  { tone: "likely", label: "Likely" },
  { tone: "unverified", label: "Unverified" },
  { tone: "disputed", label: "Disputed" },
];

export default function TonightPage() {
  const [status, setStatus] = useState<Status>("loading");
  const [events, setEvents] = useState<TonightEvent[]>([]);
  const now = useMemo(() => new Date(), []);

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const data = await fetchTonight({ city: CITY, hours: 12, limit: 60 });
      setEvents(data);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Group by day label ("Tonight", "Sat, Jul 12", ...) preserving API order,
  // which is already sorted by confidence-tier then start_time.
  const groups = useMemo(() => {
    const out: { label: string; items: TonightEvent[] }[] = [];
    for (const ev of events) {
      const label = formatDayLabel(ev.start_time, now);
      const last = out[out.length - 1];
      if (last && last.label === label) last.items.push(ev);
      else out.push({ label, items: [ev] });
    }
    return out;
  }, [events, now]);

  return (
    <main className="pub-wrap">
      <header className="pub-header">
        <a className="pub-brand" href="/tonight" aria-label="OneLive home">
          <BrandMark size={26} />
          <span className="pub-brand-name">One<b>Live</b></span>
        </a>
        <span className="pub-city" data-testid="text-city">{CITY}, TX</span>
      </header>

      <section className="pub-hero">
        <p className="pub-kicker">Live right now</p>
        <h1 className="pub-title">What&rsquo;s happening tonight</h1>
        <p className="pub-sub">
          Music, art, food, and culture across Austin and the surrounding counties.
          Every listing shows how well we&rsquo;ve verified it &mdash; so you always
          know what you&rsquo;re looking at.
        </p>
      </section>

      <div className="pub-legend" aria-label="What the confidence labels mean">
        <span className="pub-legend-title">How verified is it?</span>
        {LEGEND.map((l) => (
          <span className="pub-legend-item" key={l.tone}>
            <span className="pub-badge" data-tone={l.tone} style={{ padding: "3px 8px" }}>
              <span className="pub-badge-dot" aria-hidden="true" />
              {l.label}
            </span>
          </span>
        ))}
      </div>

      {status === "loading" ? <FeedSkeleton /> : null}
      {status === "error" ? <FeedError onRetry={load} /> : null}
      {status === "ready" && events.length === 0 ? <FeedEmpty city={CITY} /> : null}

      {status === "ready" && events.length > 0 ? (
        <div data-testid="feed-events">
          {groups.map((g) => (
            <section key={g.label} aria-label={g.label}>
              <h2 className="pub-daygroup-label">{g.label}</h2>
              <div className="pub-feed">
                {g.items.map((ev) => (
                  <EventCard key={ev.event_id} event={ev} now={now} />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : null}

      <footer className="pub-footer">
        OneLive shows verified and unverified listings side by side, labeled honestly.
        Disputed events are shown on purpose &mdash; verify before you go.
      </footer>
    </main>
  );
}
