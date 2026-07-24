import "./flow.css";
import {
  fetchLicensedEvents,
  supabaseConfigured,
  type LicensedEvent,
} from "../../../lib/licensed";
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
    events = await fetchLicensedEvents({ fromISO });
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
