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
  originLink,
  sourceCredit,
  telHref,
  venueWebsite,
  resolveDetailView,
  statusNote,
} from "../../../../lib/detail";
import ShareButton from "./ShareButton";
import { shareCaveat } from "../../../../lib/share";
import { contextualPreview } from "../../../../lib/preview";
import { qaFixtureEventById, qaFixturesEnabled } from "../../../../qa/fixtures";
import { domainLabel } from "../../../../lib/domains";
import { externalAriaLabel, handoffCaption } from "../../../../lib/nav";

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
  const fallback = { title: "A show — 1LIVE" };
  try {
    // QA fixture mode makes no network reads anywhere — the generic title is
    // the honest metadata for a synthetic page (never shared/unfurled anyway).
    if (qaFixturesEnabled()) return fallback;
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
    const title = `${e.title} — 1LIVE`;

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
        {qaFixturesEnabled() ? (
          <div className="qanote" role="note">
            SYNTHETIC QA FIXTURES — fictional events for rendering checks, not real listings
          </div>
        ) : null}
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

  // QA fixture mode (web/qa/fixtures.ts): serve the synthetic row, no network.
  // The same resolveDetailView branch logic runs on it, so the fixture page
  // exercises the real render path, not a parallel one.
  const qa = qaFixturesEnabled();
  const configured = qa || supabaseConfigured();
  const route = configured ? routeForEventId(id) : null;

  let event: LicensedEvent | null = null;
  let error: string | null = null;
  if (route) {
    if (qa) {
      // Look up by the WHOLE id, not the routed inner one: a promoted fixture's
      // id carries the "promoted:" prefix, and routing on it would send the
      // lookup a stripped key that matches no fixture — the promoted surfaces
      // would then be unreachable in the very mode that pins them.
      event = qaFixtureEventById(id);
    } else {
      try {
        event = route.kind === "promoted"
          ? await fetchPromotedEventById(route.id)
          : await fetchLicensedEventById(route.id);
      } catch (e) {
        // Loud, never an empty page dressed as "no such event".
        error = e instanceof Error ? e.message : "Could not load this event";
      }
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
  // Contextual preview (preview.ts): the polymorphic, type-aware "hook" — music
  // → tracks, a talk → lectures, film → the trailer, an artist → their work.
  // Honest by construction (a search, never a claim); an un-previewable type
  // yields null (an honest gap, no filler).
  const preview = contextualPreview(event_);
  // Who listed this, as a fact of its own (founder 2026-09-01) — name + link
  // when the row carries them, the generic phrase only when it does not.
  const credit = sourceCredit(event_);

  return (
    <Shell>
      <article className="detail">
        {/* A catalog row outside the CAPCOG test region renders, LABELLED — it
            used to be refused outright, which the Coverage Law (2026-09-01)
            repealed: the region is a view scope, and a legally-seen row is
            never deleted, only scoped out of the default view. */}
        {view.outsideRegion ? (
          <p className="dstatus">
            This listing is outside the CAPCOG test region the default Tonight
            view scopes to. It is in the catalog; it just isn&rsquo;t in that view.
          </p>
        ) : null}
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
                <a href={map} target="_blank" rel="noopener noreferrer"
                  aria-label={externalAriaLabel("Open the address in maps", map)}>
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
                {/* The human label, not the raw slug — the card already renders
                    domainLabel; the detail page must not drift ("live-music"
                    was reaching readers here). */}
                {domainLabel(event_.category)}
                {event_.subsegment ? <span className="dsub"> · {event_.subsegment}</span> : null}
              </dd>
            </>
          ) : null}

          {/* WHO LISTED IT. A first-class fact, not prose buried in the trust
              sheet: the confirmed/likely sheet wordings name the source, but
              the unverified and disputed wordings are generic by design, so
              without this row the rows a reader most needs to check were
              exactly the ones that never said who listed them. The name links
              the source's own SITE (origin_url is the registry base_url, not a
              per-event page — the label claims no more than that). */}
          <dt>Source</dt>
          <dd>
            {credit.url ? (
              <a href={credit.url} target="_blank" rel="noopener noreferrer"
                aria-label={externalAriaLabel(`${credit.name} — the source's site`, credit.url)}>
                {credit.name} ↗
              </a>
            ) : credit.name}
          </dd>

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
                  <a href={website} target="_blank" rel="noopener noreferrer"
                    aria-label={externalAriaLabel("Venue website", website)}>
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
          {/* TERMINAL handoff (nav canon §8): same-tab, honestly labeled with
              where it finishes — Back returns here, never a stranded tab. */}
          {tix ? (
            <a className="dtix" href={tix} aria-label={externalAriaLabel("Tickets", tix)}>
              Tickets ↗{handoffCaption(tix) ? <span className="dhand"> · {handoffCaption(tix)}</span> : null}
            </a>
          ) : null}
          <ShareButton event={event_} />
        </div>

        {/* Contextual preview (preview.ts): the type-aware hook — a search on
            the user's own service, never a claim. The label varies by event
            type ("Hear them" / "Watch a talk" / "Watch the trailer" …). */}
        {preview ? (
          <div className="dlisten">
            <span className="dlisten-l">{preview.label}:</span>
            {preview.links.map((l) => (
              <a key={l.service} href={l.url} target="_blank" rel="noopener noreferrer"
                aria-label={externalAriaLabel(`${preview.label} on ${l.service}`, l.url)}>
                {l.service} ↗
              </a>
            ))}
          </div>
        ) : null}

        {/* Trust display: the SAME trustDisplay the card uses, so the two
            surfaces cannot drift into different claims about one row. Quiet
            marker plus a dismissible sheet — no badges, no "confirmed".
            The disclosure renders for EVERY state (the lens already shows
            provenance on every tab — a confirmed event's full page saying
            nothing about how we know it was the drift this comment claims
            impossible); cautious states additionally carry their marker, and
            disputed opens the sheet by default, exactly as before. */}
        <details className="dunc" open={trust.disputed}>
          <summary>
            {trust.surface && trust.marker ? (
              <><span className={`cau${trust.disputed ? " disp" : ""}`}>{trust.marker}</span>{" "}</>
            ) : null}
            How we know
          </summary>
          <div className="sheet">
            {trust.sheet}
            {originLink(event_) ? (
              <>
                {" "}
                {/* origin_url is the source's registered base_url, not a
                    per-event page — the copy claims exactly that (evaluator
                    #188 r1). */}
                <a href={originLink(event_)!} target="_blank" rel="noopener noreferrer"
                  aria-label={externalAriaLabel("See the source's site", originLink(event_)!)}>
                  See the source&rsquo;s site ↗
                </a>
              </>
            ) : null}
          </div>
        </details>
      </article>
    </Shell>
  );
}
