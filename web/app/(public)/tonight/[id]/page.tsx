import Link from "next/link";
import "../flow.css";
import "./detail.css";
import {
  fetchLicensedEventById,
  supabaseConfigured,
  type LicensedEvent,
} from "../../../../lib/licensed";
import {
  fetchPromotedEventById,
  routeForEventId,
} from "../../../../lib/promoted";
import { trustDisplay } from "../../../../lib/trust";
import {
  detailProviderLabel,
  detailTrustKind,
  detailPrice,
  detailWhen,
  detailMapUrl,
  httpOrNull,
  statusNote,
} from "../../../../lib/detail";

// Server component — reads ONE event at request time. Deliberately NOT cached:
// the same freshness rule the feed uses, for the same reason (an event that
// moved or was cancelled must not be served from a stale render).
export const dynamic = "force-dynamic";

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="flow">
      <div className="wrap">
        <div className="mast">
          <h1>
            <Link className="back" href="/tonight">
              ← Tonight in Austin
            </Link>
          </h1>
        </div>
        {children}
      </div>
    </main>
  );
}

export default async function EventDetailPage(
  { params }: { params: Promise<{ id: string }> },
) {
  const { id: rawId } = await params;
  const id = decodeURIComponent(rawId);

  if (!supabaseConfigured()) {
    return (
      <Shell>
        <div className="err">
          Connecting to live data… set <b>SUPABASE_URL</b> and{" "}
          <b>SUPABASE_ANON_KEY</b> in the deployment environment and redeploy.
        </div>
      </Shell>
    );
  }

  const route = routeForEventId(id);
  if (!route) {
    return (
      <Shell>
        <div className="err">That link doesn&rsquo;t point at an event.</div>
      </Shell>
    );
  }

  let event: LicensedEvent | null = null;
  let error: string | null = null;
  try {
    event = route.kind === "promoted"
      ? await fetchPromotedEventById(route.id)
      : await fetchLicensedEventById(route.id);
  } catch (e) {
    // Loud, never an empty page dressed as "no such event".
    error = e instanceof Error ? e.message : "Could not load this event";
  }

  if (error) {
    return (
      <Shell>
        <div className="err">Couldn&rsquo;t load this event: {error}</div>
      </Shell>
    );
  }
  if (!event) {
    return (
      <Shell>
        <div className="err">
          We don&rsquo;t have an event at this link. It may have been removed by
          the venue or organizer.
        </div>
      </Shell>
    );
  }

  const trust = trustDisplay(
    event.confidence,
    detailProviderLabel(event),
    detailTrustKind(event),
  );
  const price = detailPrice(event);
  const map = detailMapUrl(event);
  const tix = httpOrNull(event.ticket_url);
  const img = httpOrNull(event.image_url);
  const note = statusNote(event);

  return (
    <Shell>
      <article className="detail">
        {img ? (
          <div className="dph" style={{ backgroundImage: `url(${img})` }} />
        ) : null}

        <h2 className="dti">{event.title}</h2>
        {event.performer ? <p className="dperf">{event.performer}</p> : null}

        {/* An event that was cancelled or moved SAYS so. The feed filters these
            out of a list nobody asked for by name; a visitor who followed a
            link to this event asked for this event. */}
        {note ? <p className="dstatus">{note}</p> : null}

        <dl className="dfacts">
          <dt>When</dt>
          <dd>{detailWhen(event)}</dd>

          <dt>Where</dt>
          <dd>
            {event.venue_name ?? "Venue not listed"}
            {event.venue_area ? <span className="dsub"> · {event.venue_area}</span> : null}
            {event.venue_address && map ? (
              <>
                <br />
                <a href={map} target="_blank" rel="noopener noreferrer">
                  {event.venue_address} ↗
                </a>
              </>
            ) : null}
          </dd>

          <dt>Price</dt>
          <dd className={price.free ? "dfree" : undefined}>{price.text}</dd>

          {event.category ? (
            <>
              <dt>Kind</dt>
              <dd>
                {event.category}
                {event.subsegment ? <span className="dsub"> · {event.subsegment}</span> : null}
              </dd>
            </>
          ) : null}
        </dl>

        {tix ? (
          <a className="dtix" href={tix} target="_blank" rel="noopener noreferrer">
            Tickets ↗
          </a>
        ) : null}

        {/* Trust display: the SAME trustDisplay the card uses, so the two
            surfaces cannot drift into different claims about one row. Quiet
            marker plus a dismissible sheet — no badges, no "confirmed". */}
        {trust.surface && trust.marker ? (
          <details className="dunc" open={trust.disputed}>
            <summary>
              <span className={`cau${trust.disputed ? " disp" : ""}`}>{trust.marker}</span>{" "}
              How we know
            </summary>
            <div className="sheet">{trust.sheet}</div>
          </details>
        ) : null}
      </article>
    </Shell>
  );
}
