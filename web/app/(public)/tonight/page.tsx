import "./flow.css";
import {
  fetchLicensedEvents,
  supabaseConfigured,
  type LicensedEvent,
} from "../../../lib/licensed";
import { fetchPromotedEvents } from "../../../lib/promoted";
import { filterToCapcog } from "../../../lib/region";
import FeedApp from "./FeedApp";

// Server component — reads the REAL licensed events from Supabase at request
// time and hands them to the interactive client feed (date/filter/ask/plan).
// The fetch never filters on confidence (disputed always included); it starts a
// little before "now" so events already in progress are still surfaced, and the
// client hides only what has genuinely ended (a time filter, never a trust one).
export const dynamic = "force-dynamic";

export default async function TonightPage() {
  if (!supabaseConfigured()) {
    return (
      <main className="flow">
        <div className="wrap">
          <div className="mast"><h1>ONE LIVE · Tonight in Austin</h1></div>
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
    // licensed rows (Ticketmaster/SeatGeek/…) PLUS pipeline-promoted long-tail
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
    events = region.kept;
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load events";
  }

  if (error) {
    return (
      <main className="flow">
        <div className="wrap">
          <div className="mast"><h1>ONE LIVE · Tonight in Austin</h1></div>
          <div className="err">Couldn&rsquo;t load events: {error}</div>
        </div>
      </main>
    );
  }

  return <FeedApp events={events} serverNowMs={nowMs} />;
}
