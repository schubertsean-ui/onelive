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
  telHref,
  venueWebsite,
  resolveDetailView,
  statusNote,
} from "../../../../lib/detail";
import ShareButton from "./ShareButton";
import { shareCaveat } from "../../../../lib/share";
import { listenLinks } from "../../../../lib/listen";

// Server component — reads ONE event at request time. Deliberately NOT cached:
// the same freshness rule the feed uses, for the same reason (an event that
// moved or was cancelled must not be served from a stale render).
export const dynamic = "force-dynamic";

// Open Graph / Twitter tags so a SHARED link (group-plans P0 / brief §6.D5)
// unfurls as a compact card in Messages, iMessage, WhatsApp, etc. — that link
// preview IS the "share card" in a texting context. Trust rules hold here too:
// the description states facts the row carries (when · venue · known price),
// never a badge or "confirmed", and a disputed event says so. Best-effort and
// never throws — a metadata read that fails degrades to the generic title.
export async function generateMetadata(
  { params }: { params: Promise<{ id: string }> },
) {
  const fallback = { title: "A show — ONE LIVE" };
  try {
    if (!supabaseConfigured()) return fallback;
    const { id } = await params;
    const route = routeForEventId(id);
    if (!route) return fallback;
    const e = route.kind === "promoted"
      ? await fetchPromotedEventById(route.id)
      : await fetchLicensedEventById(route.id);
    if (!e) return fallback;

    const price = detailPrice(e);
    // The link preview carries the SAME status/uncertainty caveat as the share
    // text (shareCaveat): a cancelled/postponed/moved event, or a non-confirmed
    // row, must not unfurl in Messages as an ordinary upcoming show.
    const desc = [
      detailWhen(e),
      [e.venue_name, e.venue_area].filter(Boolean).join(" · ") || null,
      price.known ? price.text : null,
      shareCaveat(e),
    ].filter(Boolean).join(" · ");
    const img = httpOrNull(e.image_url);
    const title = `${e.title} — ONE LIVE`;

    return {
      title,
      description: desc,
      openGraph: {
        title,
        description: desc,
        type: "website",
        ...(img ? { images: [{ url: img }] } : {}),
      },
      twitter: {
        card: img ? "summary_large_image" : "summary",
        title,
        description: desc,
      },
    };
  } catch {
    return fallback;
  }
}

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
  // Next 15's App Router hands `params` ALREADY DECODED, so decoding again was
  // wrong (PR #87 r3, gemini dataflow-taint): it is a no-op for ordinary ids
  // and corrupts any id containing a literal percent sign, turning a valid
  // link into "no such event". The value is used as-is; routeForEventId
  // rejects the empty and prefix-only cases.
  const { id } = await params;

  const configured = supabaseConfigured();
  const route = configured ? routeForEventId(id) : null;

  let event: LicensedEvent | null = null;
  let error: string | null = null;
  if (route) {
    try {
      event = route.kind === "promoted"
        ? await fetchPromotedEventById(route.id)
        : await fetchLicensedEventById(route.id);
    } catch (e) {
      // Loud, never an empty page dressed as "no such event".
      error = e instanceof Error ? e.message : "Could not load this event";
    }
  }

  // The branch choice is made by resolveDetailView, which is unit-tested; this
  // component only renders the answer (PR #87 r3, class missing-contract-test).
  const view = resolveDetailView({ configured, routed: route !== null, error, event });

  if (view.kind === "unconfigured") {
    return (
      <Shell>
        <div className="err">
          Connecting to live data… set <b>NEXT_PUBLIC_SUPABASE_URL</b> and{" "}
          <b>NEXT_PUBLIC_SUPABASE_ANON_KEY</b> (the publishable key) in the
          deployment environment and redeploy.
        </div>
      </Shell>
    );
  }
  if (view.kind === "bad-link") {
    return (
      <Shell>
        <div className="err">That link doesn&rsquo;t point at an event.</div>
      </Shell>
    );
  }
  if (view.kind === "read-error") {
    return (
      <Shell>
        <div className="err">Couldn&rsquo;t load this event: {view.message}</div>
      </Shell>
    );
  }
  if (view.kind === "not-found") {
    return (
      <Shell>
        <div className="err">
          We don&rsquo;t have an event at this link. It may have been removed by
          the venue or organizer.
        </div>
      </Shell>
    );
  }

  const event_ = view.event;

  const trust = trustDisplay(
    event_.confidence,
    detailProviderLabel(event_),
    detailTrustKind(event_),
  );
  const price = detailPrice(event_);
  const map = detailMapUrl(event_);
  const tix = httpOrNull(event_.ticket_url);
  const img = httpOrNull(event_.image_url);
  const note = statusNote(event_);
  // Venue contact — the venue is always the last word, so make confirming easy:
  // a website link and a one-tap call. The website shows only when it's the
  // venue's OWN site (not a ticketing-provider page — venueWebsite drops those);
  // the call shows only when the number is dialable.
  const website = venueWebsite(event_.venue_url);
  const call = telHref(event_.venue_phone);
  // "Hear them" (music player, Option A): search links to the act on the major
  // services — MUSIC events with a named performer only ("hear them on Spotify"
  // is nonsense for a lecture or exhibition).
  const isMusic = event_.category === "live-music" || event_.category === "nightlife";
  const listen = isMusic ? listenLinks(event_.performer) : [];

  return (
    <Shell>
      <article className="detail">
        {/* An <img> element, NOT a CSS background (PR #87 r3, gemini
            dataflow-taint): `url(${img})` interpolates a stored value straight
            into CSS, and a perfectly valid https URL containing `')` breaks out
            of url() into arbitrary CSS. React escapes an attribute; a template
            string in a style object escapes nothing. It is also the better
            element — it can carry alt text and be sized by the browser. */}
        {img ? (
          <img className="dph" src={img} alt={event_.title} />
        ) : null}

        <h2 className="dti">{event_.title}</h2>
        {event_.performer ? <p className="dperf">{event_.performer}</p> : null}

        {/* An event that was cancelled or moved SAYS so. The feed filters these
            out of a list nobody asked for by name; a visitor who followed a
            link to this event asked for this event. */}
        {note ? <p className="dstatus">{note}</p> : null}

        <dl className="dfacts">
          <dt>When</dt>
          <dd>{detailWhen(event_)}</dd>

          <dt>Where</dt>
          <dd>
            {event_.venue_name ?? "Venue not listed"}
            {event_.venue_area ? <span className="dsub"> · {event_.venue_area}</span> : null}
            {/* Keyed on the MAP link, not on the address (gemini nit): a
                venue with coordinates but no street address still deserves a
                map, and the feed already behaves this way. */}
            {map ? (
              <>
                <br />
                <a href={map} target="_blank" rel="noopener noreferrer">
                  {event_.venue_address ?? "Open in maps"} ↗
                </a>
              </>
            ) : null}
          </dd>

          <dt>Price</dt>
          <dd className={price.free ? "dfree" : undefined}>{price.text}</dd>

          {event_.category ? (
            <>
              <dt>Kind</dt>
              <dd>
                {event_.category}
                {event_.subsegment ? <span className="dsub"> · {event_.subsegment}</span> : null}
              </dd>
            </>
          ) : null}

          {/* Check with the venue — the last word on any listing. Shown only
              when we have a real website and/or a dialable number. */}
          {(website || call) ? (
            <>
              <dt>Check the venue</dt>
              <dd className="dcontact">
                {call ? (
                  <a className="dcall" href={call}>📞 Want to call and confirm?</a>
                ) : null}
                {website ? (
                  <a href={website} target="_blank" rel="noopener noreferrer">
                    Venue website ↗
                  </a>
                ) : null}
              </dd>
            </>
          ) : null}
        </dl>

        {/* Tickets + Share. Share is always offered (it needs nothing but a
            link); Tickets appears only when the row carries a real ticket URL. */}
        <div className="dactions">
          {tix ? (
            <a className="dtix" href={tix} target="_blank" rel="noopener noreferrer">
              Tickets ↗
            </a>
          ) : null}
          <ShareButton event={event_} />
        </div>

        {/* Hear them (music player, Option A): search the act on the services
            the listener already uses. A preview, not a claim — opens their own
            Spotify/Apple/YouTube search. Music events with a performer only. */}
        {listen.length ? (
          <div className="dlisten">
            <span className="dlisten-l">Hear them:</span>
            {listen.map((l) => (
              <a key={l.service} href={l.url} target="_blank" rel="noopener noreferrer">
                {l.service} ↗
              </a>
            ))}
          </div>
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
