// SYNTHETIC QA fixtures for deterministic rendering (visual regression, R-002;
// a11y audits). Every event here is FICTIONAL — fictional acts, fictional
// venues, reserved 555 phone numbers, example.com links — so no fact is ever
// asserted about a real act or venue (trust rule: never fabricate). The pages
// render a visible "SYNTHETIC QA FIXTURES" note whenever this mode is on, so a
// fixture render can never be mistaken for the real product.
//
// FAIL-CLOSED: the mode is off unless the server env carries EXACTLY
// ONELIVE_QA_FIXTURES=1. It is never set in any deployment environment — it is
// set only by tools/visual_check.sh (local + CI capture) — and when off, the
// real read path runs untouched. Display-only: nothing here writes anywhere,
// nothing enters candidate/event data, and the fixture branch lives in the two
// page components where a reviewer can see it, not inside the data layer.
//
// DETERMINISM: the clock is frozen at QA_FROZEN_NOW_MS and every start_time is
// a fixed offset from it, so date buckets, tabs, "on now", and labels are
// stable forever. Render with TZ=America/Chicago (server AND browser) — the
// feed formats in that zone and day boundaries use local time. No fixture
// carries an image URL: capture runs offline, and an external image would make
// pixels depend on the network. The image-less domain-hued cover is itself
// canon (PR #147) and is what the baselines pin.
import type { LicensedEvent } from "../lib/licensed";

export function qaFixturesEnabled(): boolean {
  return process.env.ONELIVE_QA_FIXTURES === "1";
}

// Thu 2026-10-15 20:30 CDT — a frozen "tonight". Weekday labels, "Today"/
// "Tomorrow" tabs, and the three density tiers all derive from this instant.
export const QA_FROZEN_NOW_MS = Date.UTC(2026, 9, 16, 1, 30, 0); // 2026-10-16T01:30:00Z

const H = 3_600_000;
const D = 24 * H;
const iso = (offsetMs: number) => new Date(QA_FROZEN_NOW_MS + offsetMs).toISOString();

// Shared fictional-venue scaffold. Address/coords are inside Austin (CAPCOG)
// so the detail surface's market-boundary check keeps the row, but the venue
// itself does not exist.
function venue(n: number, name: string, area: string) {
  return {
    venue_name: name,
    venue_city: "Austin",
    venue_area: area,
    venue_address: `${100 + n} Fictional St`,
    venue_lat: 30.2672,
    venue_lng: -97.7431,
    venue_url: `https://qa-venue-${n}.example.com`,
    venue_phone: `+1512555010${n}`,
  };
}

function base(n: number, over: Partial<LicensedEvent>): LicensedEvent {
  return {
    licensed_event_id: `qa-${n}`,
    source_provider: "ticketmaster",
    external_id: `qa-ext-${n}`,
    title: `QA Fixture Event ${n}`,
    category: "live-music",
    subsegment: null,
    performer: null,
    start_time: null,
    end_time: null,
    status: "scheduled",
    on_sale_status: null,
    price_min: null,
    price_max: null,
    currency: "USD",
    is_free: null,
    ticket_url: null,
    image_url: null, // never an image: offline determinism + pins the #147 cover
    confidence: "confirmed",
    ...venue(n, `Fictional Hall ${n}`, "Downtown"),
    ...over,
  };
}

// The fixture set — chosen to exercise, in one screen, every display rule the
// canon makes physics: all four confidence states (disputed SHOWN, §8), the
// free pill, "on now", both Spark Line registers (tier B attribution, tier C ✳),
// the image-less domain-hued cover, the contextual preview per type, and all
// three density tiers (rich ≤7d / compact 8–30d / line >30d).
export function qaFixtureEvents(): LicensedEvent[] {
  return [
    // Tonight, already under way → "on now"; tier-B Spark Line with attribution.
    base(1, {
      title: "The Copper Owls",
      performer: "The Copper Owls",
      subsegment: "Rock",
      start_time: iso(-0.5 * H),
      end_time: iso(1.5 * H),
      price_min: 15,
      price_max: 20,
      ticket_url: "https://tickets.example.com/qa-1",
      artist_ref: "qa-ref-1",
      spark: { text: "brass. menace. amen.", tier: "B", attribution: "QA Weekly" },
      ...venue(1, "The Blue Kiln", "East Austin"),
    }),
    // Tonight, free comedy → mint Free pill; likely → "single source" marker.
    base(2, {
      title: "Open Mic: Synthetic Laughs",
      performer: "Ada Fictional",
      category: "comedy",
      start_time: iso(1 * H),
      is_free: true,
      price_min: 0,
      confidence: "likely",
      ...venue(2, "Laugh Fixture Lounge", "Red River"),
    }),
    // Tonight, a lecture → "Watch a talk" preview; unverified marker.
    base(3, {
      title: "How Cities Hear Themselves",
      performer: "Dr. Rivera Notreal",
      category: "ideas",
      start_time: iso(2 * H),
      price_min: 10,
      confidence: "unverified",
      ...venue(3, "The Fictional Forum", "Campus"),
    }),
    // Tonight, DISPUTED — shown, never hidden; the marker is the stronger one.
    base(4, {
      title: "Midnight Static",
      performer: "Midnight Static",
      subsegment: "Electronic",
      start_time: iso(3 * H),
      price_min: 12,
      confidence: "disputed",
      ticket_url: "https://tickets.example.com/qa-4",
      ...venue(4, "Warehouse Nowhere", "East Austin"),
    }),
    // Tomorrow, tier-C AI-drafted Spark Line → the quiet ✳ register (§4).
    base(5, {
      title: "Petal & Bone",
      performer: "Petal & Bone",
      subsegment: "Folk",
      start_time: iso(D - 1 * H),
      price_min: 18,
      artist_ref: "qa-ref-5",
      spark: { text: "porch hymns, slow and holy", tier: "C", attribution: "first notes" },
      ...venue(5, "The Paper Lantern", "South Austin"),
    }),
    // +3 days, food & drink, unknown price → honest "See tickets".
    base(6, {
      title: "Fermentation Fair (Fictional)",
      category: "food-drink",
      start_time: iso(3 * D),
      ...venue(6, "QA Cider Yard", "Hill Country"),
    }),
    // +12 days → the compact "coming weeks" row.
    base(7, {
      title: "Gallery Night: Invented Frames",
      category: "visual-arts",
      start_time: iso(12 * D),
      is_free: true,
      price_min: 0,
      ...venue(7, "Museum of Made-Up Art", "Downtown"),
    }),
    // +45 days → the tersest "line" tier; trust marker still rides (likely).
    base(8, {
      title: "The Long Now Quartet",
      performer: "The Long Now Quartet",
      subsegment: "Jazz",
      start_time: iso(45 * D),
      price_min: 25,
      price_max: 40,
      confidence: "likely",
      ...venue(8, "Fictional Hall 8", "Downtown"),
    }),
    // Cancelled tomorrow — the FEED drops it by status; the DETAIL page (linked
    // by id below) states it plainly. Exists so the status-note surface is
    // pinned by a baseline too.
    base(9, {
      title: "Cancelled Fixture Show",
      performer: "The Unbooked",
      start_time: iso(D + 2 * H),
      status: "cancelled",
      price_min: 20,
      ...venue(9, "The Empty Room", "North Loop"),
    }),
  ];
}

export function qaFixtureEventById(id: string): LicensedEvent | null {
  return qaFixtureEvents().find((e) => e.licensed_event_id === id) ?? null;
}
