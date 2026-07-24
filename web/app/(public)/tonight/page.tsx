import "./flow.css";
import {
  DOMAINS,
  domainHue,
  domainLabel,
  timeBand,
} from "../../../lib/domains";
import {
  fetchLicensedEvents,
  supabaseConfigured,
  type LicensedEvent,
} from "../../../lib/licensed";

// Server component — reads the REAL licensed events from Supabase at request
// time. No confidence badges (trust display rule); uncertainty is a quiet
// <details>. Time-tiered density: rich cards this week, condensed rows later.
export const dynamic = "force-dynamic";

function fmtWhen(iso: string | null): string {
  if (!iso) return "Date TBA";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Date TBA";
  return d.toLocaleString("en-US", {
    timeZone: "America/Chicago",
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function fmtPrice(e: LicensedEvent): { text: string; free: boolean } {
  if (e.is_free) return { text: "Free", free: true };
  if (e.price_min != null && e.price_max != null && e.price_max !== e.price_min) {
    return { text: `$${Math.round(e.price_min)}–$${Math.round(e.price_max)}`, free: false };
  }
  if (e.price_min != null) return { text: `$${Math.round(e.price_min)}`, free: false };
  return { text: "See tickets", free: false };
}

function mapUrl(e: LicensedEvent): string | null {
  if (e.venue_lat != null && e.venue_lng != null) {
    return `https://www.google.com/maps/search/?api=1&query=${e.venue_lat},${e.venue_lng}`;
  }
  const q = [e.venue_name, e.venue_address, e.venue_city].filter(Boolean).join(", ");
  return q ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}` : null;
}

function focusLine(e: LicensedEvent): string {
  const parts = [domainLabel(e.category), e.subsegment].filter(Boolean);
  // Avoid "Live Music · Live Music"-style repeats.
  return parts.filter((v, i) => parts.indexOf(v) === i).join(" · ");
}

function RichCard({ e }: { e: LicensedEvent }) {
  const price = fmtPrice(e);
  const map = mapUrl(e);
  return (
    <div className="card">
      {e.image_url ? (
        <div className="ph" style={{ backgroundImage: `url(${e.image_url})` }} />
      ) : (
        <div
          className="noph"
          style={{ background: `linear-gradient(90deg, hsl(${domainHue(e.category)} 60% 45%), hsl(${(domainHue(e.category) + 40) % 360} 55% 38%))` }}
        />
      )}
      <div className="bd">
        <span className="when">{fmtWhen(e.start_time)}</span>
        <span className="ti">{e.title}</span>
        <span className="focus">{focusLine(e)}</span>
        <span className="ven">
          {e.venue_name}
          {e.venue_area ? <span className="addr"> · {e.venue_area}</span> : null}
          {e.venue_address ? <span className="addr"> · {e.venue_address}</span> : null}
        </span>
        <div className="foot">
          <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
          {e.ticket_url ? (
            <a className="tix" href={e.ticket_url} target="_blank" rel="noopener noreferrer">
              tickets ↗
            </a>
          ) : null}
          {map ? (
            <a className="map" href={map} target="_blank" rel="noopener noreferrer">
              map ↗
            </a>
          ) : null}
        </div>
        <details className="unc">
          <summary>How we know</summary>
          <div className="sheet">
            Listed by {e.source_provider === "ticketmaster" ? "Ticketmaster" : e.source_provider} —
            an authoritative ticketing source. Times and prices can change; the
            venue&rsquo;s own page and the ticket link are the last word.
          </div>
        </details>
      </div>
    </div>
  );
}

function CondensedRow({ e }: { e: LicensedEvent }) {
  const price = fmtPrice(e);
  return (
    <div className="row">
      <span className="when">{fmtWhen(e.start_time)}</span>
      <span className="bd2">
        <span className="ti">{e.title}</span>
        <br />
        <span className="mt">
          {focusLine(e)} · {e.venue_name}
          {e.venue_area ? ` · ${e.venue_area}` : ""}
        </span>
      </span>
      <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
    </div>
  );
}

export default async function TonightPage() {
  if (!supabaseConfigured()) {
    return (
      <main className="flow">
        <div className="wrap">
          <div className="mast">
            <h1>ONE LIVE · Tonight in Austin</h1>
          </div>
          <div className="err">
            Connecting to live data… set <b>NEXT_PUBLIC_SUPABASE_URL</b> and{" "}
            <b>NEXT_PUBLIC_SUPABASE_ANON_KEY</b> (the Supabase publishable key) in the
            deployment environment and redeploy.
          </div>
        </div>
      </main>
    );
  }

  let events: LicensedEvent[] = [];
  let error: string | null = null;
  try {
    const nowISO = new Date().toISOString();
    events = await fetchLicensedEvents({ fromISO: nowISO, limit: 1000 });
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load events";
  }

  const nowMs = Date.now();
  const total = events.length;
  const freeCount = events.filter((e) => e.is_free).length;
  const byDomain = new Map<string, LicensedEvent[]>();
  for (const e of events) {
    const k = e.category ?? "unmapped";
    const arr = byDomain.get(k);
    if (arr) arr.push(e);
    else byDomain.set(k, [e]);
  }
  const activeDomains = DOMAINS.filter((d) => (byDomain.get(d.id)?.length ?? 0) > 0);

  return (
    <main className="flow">
      <div className="demobar">
        Real, licensed events for the CAPCOG area — live from Ticketmaster. Private
        preview: not public, behind the stealth gate before launch.
      </div>
      <div className="wrap">
        <div className="mast">
          <h1>ONE LIVE · Tonight in Austin</h1>
          <p className="lede">
            Everything on in Central Texas, in one place. Real events, real venues,
            real prices — grouped by what kind of night you want.
          </p>
          <div className="kpis">
            <div className="kpi"><div className="v">{total.toLocaleString()}</div><div className="l">upcoming events</div></div>
            <div className="kpi"><div className="v">{activeDomains.length}</div><div className="l">cultural domains</div></div>
            <div className="kpi"><div className="v">{total ? Math.round((100 * freeCount) / total) : 0}%</div><div className="l">free to attend</div></div>
          </div>
        </div>

        {error ? (
          <div className="err">Couldn&rsquo;t load events: {error}</div>
        ) : total === 0 ? (
          <div className="err">No upcoming events found yet — the next import will populate the feed.</div>
        ) : (
          <>
            <nav className="domnav">
              {activeDomains.map((d) => (
                <a key={d.id} href={`#${d.id}`}>
                  <span className="dot" style={{ background: `hsl(${d.hue} 65% 55%)` }} />
                  {d.label}
                  <span className="n">{byDomain.get(d.id)!.length}</span>
                </a>
              ))}
            </nav>

            {activeDomains.map((d) => {
              const items = byDomain.get(d.id)!;
              const rich = items.filter((e) => timeBand(e.start_time, nowMs) === "rich");
              const later = items.filter((e) => timeBand(e.start_time, nowMs) !== "rich");
              return (
                <section key={d.id} id={d.id}>
                  <div className="sec">
                    <span className="dot" style={{ background: `hsl(${d.hue} 65% 55%)`, width: 12, height: 12 }} />
                    <h2>{d.label}</h2>
                    <span className="n">{items.length}</span>
                  </div>
                  {rich.length > 0 ? (
                    <div className="grid">
                      {rich.slice(0, 12).map((e) => (
                        <RichCard key={e.licensed_event_id} e={e} />
                      ))}
                    </div>
                  ) : null}
                  {later.length > 0 ? (
                    <div style={{ display: "grid", gap: 8, marginTop: rich.length ? 10 : 0 }}>
                      {later.slice(0, 20).map((e) => (
                        <CondensedRow key={e.licensed_event_id} e={e} />
                      ))}
                    </div>
                  ) : null}
                </section>
              );
            })}
          </>
        )}

        <footer>
          Real, licensed listings from authoritative ticketing sources — never
          fabricated. Times and prices can change; each listing links to the
          venue/ticket source as the last word. The long-tail domains (libraries,
          lectures, readings, heritage, block parties) are being added from OneLive&rsquo;s
          own pipeline; what you see here is the ticketed spine.
        </footer>
      </div>
    </main>
  );
}
