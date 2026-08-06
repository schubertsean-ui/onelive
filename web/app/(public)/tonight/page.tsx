import "./flow.css";
import {
  fetchLicensedEvents,
  supabaseConfigured,
  type LicensedEvent,
} from "../../../lib/licensed";
import { fetchPromotedEvents } from "../../../lib/promoted";
import { dedupeEvents } from "../../../lib/dedupe_display";
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
    // MARKET BOUNDARY, enforced at the last step before a person sees a
    // listing (evaluator blocker r2: fixing acquisition is not the same as
    // protecting the reader — rows already stored, or from any future or
    // mis-tagged source, would still reach this page). Known-outside places
    // (San Antonio, New Braunfels, Seguin, Killeen…) are DROPPED; unrecognised
    // places are KEPT and counted, because silently discarding them would turn
    // a coverage gap into an invisible one while making the feed look cleaner.
    const region = filterToCapcog<LicensedEvent>([...licensed, ...promoted]);
    if (region.droppedOutside.length) {
      console.warn(
        `[region] dropped ${region.droppedOutside.length} event(s) outside ` +
        `CAPCOG before render: ` +
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
    // Cross-source duplicate collapse (founder-caught live 2026-08-05: the
    // same show via ticketing + the venue's own feed rendered twice). Only
    // identical venue+start+title collapses; disputed rows never do; the
    // richest record is kept and the collapse is COUNTED, never silent.
    const deduped = dedupeEvents(region.kept);
    if (deduped.collapsed.length) {
      console.warn(
        `[dedupe] collapsed ${deduped.collapsed.length} cross-source duplicate ` +
        `card(s): ` +
        deduped.collapsed.map((e) => `${e.source_provider}:${e.external_id}`).join(", "),
      );
    }
    // Attach approved Spark Lines by performer (additive; never throws, never
    // reorders/filters — display only). A read failure leaves the feed unchanged.
    events = await withSparkLines(deduped.kept);
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
