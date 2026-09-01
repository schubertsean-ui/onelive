import "./flow.css";
import {
  fetchLicensedEvents,
  supabaseConfigured,
  type LicensedEvent,
} from "../../../lib/licensed";
import { fetchPromotedEvents } from "../../../lib/promoted";
import { withSparkLines } from "../../../lib/spark";
import { filterToCapcog } from "../../../lib/region";
import {
  QA_FROZEN_NOW_MS,
  qaFixtureEvents,
  qaFixturesEnabled,
} from "../../../qa/fixtures";
import FeedApp from "./FeedApp";

// Server component — reads the REAL licensed events from Supabase at request
// time and hands them to the interactive client feed (date/filter/ask/plan).
// The fetch never filters on confidence (disputed always included); it starts a
// little before "now" so events already in progress are still surfaced, and the
// client hides only what has genuinely ended (a time filter, never a trust one).
export const dynamic = "force-dynamic";

export default async function TonightPage() {
  // SYNTHETIC QA fixture mode (visual regression R-002 / a11y audits) — fully
  // fictional events, frozen clock, visible banner; fail-closed off unless the
  // server env carries ONELIVE_QA_FIXTURES=1 (never set in any deployment).
  // The status filter mirrors the ONLY filter the real query applies
  // (scheduled+moved — a time/status filter, never a confidence one).
  if (qaFixturesEnabled()) {
    const fixture = qaFixtureEvents().filter(
      (e) => e.status === "scheduled" || e.status === "moved",
    );
    return (
      <>
        <div className="qanote" role="note">
          SYNTHETIC QA FIXTURES — fictional events for rendering checks, not real listings
        </div>
        <FeedApp events={fixture} serverNowMs={QA_FROZEN_NOW_MS} qaFrozenClock />
      </>
    );
  }

  if (!supabaseConfigured()) {
    return (
      <main className="flow">
        <div className="wrap">
          <div className="mast"><h1>1LIVE · Tonight in Austin</h1></div>
          <div className="err">
            Connecting to live data… set <b>SUPABASE_URL</b> and{" "}
            <b>SUPABASE_ANON_KEY</b> (the Supabase publishable key) in the
            deployment environment and redeploy.
          </div>
        </div>
      </main>
    );
  }

  const nowMs = Date.now();
  let events: LicensedEvent[] = [];
  let error: string | null = null;
  try {
    // 12h back so an event already under way is still shown ("on now"); the
    // client drops anything actually ended.
    const fromISO = new Date(nowMs - 12 * 60 * 60 * 1000).toISOString();
    // The consumer read path is `event ∪ licensed_event` (migration 0010):
    // licensed rows (Ticketmaster/SeatGeek/…) PLUS pipeline-promoted discovered
    // events. The promoted union is ADDITIVE — if it fails we still render the
    // licensed feed (never blank a working feed over the smaller source); a
    // licensed-read failure remains the hard error, exactly as before.
    const [licensed, promoted] = await Promise.all([
      fetchLicensedEvents({ fromISO }),
      fetchPromotedEvents({ fromISO }).catch((e) => {
        console.error("promoted-event read failed; showing licensed feed only:", e);
        return [] as LicensedEvent[];
      }),
    ]);
    // MARKET BOUNDARY — a VIEW SCOPE from here on, not a server-side delete
    // (Coverage Law 2026-09-01: "CAPCOG is the TEST LOCALE and a view filter,
    // not the map … Views must not delete catalog rows").
    //
    // What changed and what did NOT: the classification is untouched
    // (lib/region.ts still decides inside/outside/unrecognised the same way,
    // and unrecognised is still KEPT), and the DEFAULT view the reader lands on
    // is still CAPCOG-only. What changed is that the page now receives the
    // whole window and applies the scope in the client, so it can (a) say how
    // many rows the scope is holding back and (b) let the reader clear it. The
    // old shape made the dropped rows unobservable, which meant the feed could
    // not tell a market boundary apart from a coverage gap — the exact
    // invisible-gap failure this file's own comment warns about, one level up.
    //
    // The boundary still holds on every surface: FeedApp scopes to CAPCOG by
    // default, and /tonight/[id] labels an outside-market row as outside rather
    // than presenting it as part of the test view.
    const all: LicensedEvent[] = [...licensed, ...promoted];
    const region = filterToCapcog<LicensedEvent>(all);
    if (region.droppedOutside.length) {
      console.warn(
        `[region] ${region.droppedOutside.length} event(s) outside CAPCOG are ` +
        `held back by the DEFAULT view scope (still in the catalog, counted in ` +
        `the "of M" total when the reader clears the region filter): ` +
        [...new Set(region.droppedOutside.map((e) => e.venue_city))].join(", "),
      );
    }
    if (region.unknown.length) {
      console.warn(
        `[region] ${region.unknown.length} event(s) have an unrecognised city ` +
        `and were SHOWN (not dropped): ` +
        [...new Set(region.unknown.map((e) => e.venue_city))].join(", "),
      );
    }
    // Attach approved Spark Lines by performer (additive; never throws, never
    // reorders/filters — display only). A read failure leaves the feed unchanged.
    events = await withSparkLines(all);
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load events";
  }

  if (error) {
    return (
      <main className="flow">
        <div className="wrap">
          <div className="mast"><h1>1LIVE · Tonight in Austin</h1></div>
          <div className="err">Couldn&rsquo;t load events: {error}</div>
        </div>
      </main>
    );
  }

  return <FeedApp events={events} serverNowMs={nowMs} />;
}
