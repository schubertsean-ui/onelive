import "./flow.css";
import "./rooms.css";
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

export const dynamic = "force-dynamic";

export default async function TonightPage() {
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
          <div className="mast"><h1>1LIVE · Austin</h1></div>
          <div className="err">
            Connecting to live data… set <b>SUPABASE_URL</b> and{" "}
            <b>NEXT_PUBLIC_SUPABASE_ANON_KEY</b> (the Supabase publishable key) in the
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
    // 36h back so a date-only start stored as YYYY-MM-DD (UTC midnight)
    // is still in the window for the Chicago day. 12h cut those rows
    // before Today could see them. Client still hides what has ended.
    const fromISO = new Date(nowMs - 36 * 60 * 60 * 1000).toISOString();
    const toISO = new Date(nowMs + 180 * 24 * 60 * 60 * 1000).toISOString();
    const window = { fromISO, toISO, includeNullClock: true as const };
    let licensedFailed = false;
    let promotedFailed = false;
    const [licensed, promoted] = await Promise.all([
      fetchLicensedEvents(window).catch((e) => {
        console.error("licensed-event read failed:", e);
        licensedFailed = true;
        return [] as LicensedEvent[];
      }),
      fetchPromotedEvents(window).catch((e) => {
        console.error("promoted-event read failed; showing licensed feed only:", e);
        promotedFailed = true;
        return [] as LicensedEvent[];
      }),
    ]);
    if (licensedFailed && promotedFailed) {
      throw new Error("Could not load events");
    }
    const all: LicensedEvent[] = [...licensed, ...promoted];
    const region = filterToCapcog<LicensedEvent>(all);
    if (region.droppedOutside.length) {
      console.warn(
        `[region] ${region.droppedOutside.length} event(s) outside CAPCOG are ` +
        `held back by the DEFAULT view scope (still in the catalog): ` +
        [...new Set(region.droppedOutside.map((e) => e.venue_city))].join(", "),
      );
    }
    events = await withSparkLines(all);
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load events";
  }

  if (error) {
    return (
      <main className="flow">
        <div className="wrap">
          <div className="mast"><h1>1LIVE · Austin</h1></div>
          <div className="err">Couldn&rsquo;t load events: {error}</div>
        </div>
      </main>
    );
  }

  return <FeedApp events={events} serverNowMs={nowMs} />;
}
