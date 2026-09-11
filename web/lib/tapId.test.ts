// Tap 400 / 22P02. A friend taps a card. The URL may carry promoted:<uuid>
// or promoted%3A<uuid>. The database column is a UUID. The encoded prefix
// must never be sent as event_id=eq.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  PROMOTED_ID_PREFIX,
  buildPromotedQuery,
  decodeEventId,
  eventIdForQuery,
  routeForEventId,
} from "./promoted";
import { eventHref } from "./detail";
import type { LicensedEvent } from "./licensed";

const LIVE_ID = "a29d0fe3-d896-4385-9e2c-9acfd4581d98";
const LIVE_ENCODED = `promoted%3A${LIVE_ID}`;
const LIVE_PREFIXED = `${PROMOTED_ID_PREFIX}${LIVE_ID}`;
const LIVE_DOUBLE = encodeURIComponent(LIVE_ENCODED);

function ev(over: Partial<LicensedEvent> = {}): LicensedEvent {
  return {
    licensed_event_id: LIVE_PREFIXED,
    source_provider: "promoted",
    external_id: LIVE_ID,
    title: "Hopdoddy",
    category: "food-drink",
    subsegment: null,
    performer: null,
    start_time: "2026-09-11T20:00:00-05:00",
    end_time: null,
    status: "scheduled",
    on_sale_status: null,
    price_min: null,
    price_max: null,
    currency: "USD",
    is_free: null,
    ticket_url: null,
    image_url: null,
    venue_name: "Hopdoddy",
    venue_city: "Austin",
    venue_area: null,
    venue_address: null,
    venue_lat: null,
    venue_lng: null,
    venue_url: null,
    venue_phone: null,
    confidence: "likely",
    ...over,
  };
}

describe("decodeEventId + routeForEventId", () => {
  it("decodes the live 400 string to promoted:uuid", () => {
    expect(decodeEventId(LIVE_ENCODED)).toBe(LIVE_PREFIXED);
    expect(decodeEventId(LIVE_DOUBLE)).toBe(LIVE_PREFIXED);
  });

  it("routes encoded, prefixed, and bare ids to the same inner uuid", () => {
    expect(routeForEventId(LIVE_ENCODED)).toEqual({ kind: "promoted", id: LIVE_ID });
    expect(routeForEventId(LIVE_PREFIXED)).toEqual({ kind: "promoted", id: LIVE_ID });
    expect(routeForEventId(LIVE_ID)).toEqual({ kind: "licensed", id: LIVE_ID });
    expect(routeForEventId(LIVE_DOUBLE)).toEqual({ kind: "promoted", id: LIVE_ID });
  });

  it("round-trips eventHref the way the phone actually navigates", () => {
    const href = eventHref(ev());
    expect(href).toBe(`/tonight/${encodeURIComponent(LIVE_PREFIXED)}`);
    const raw = href.replace("/tonight/", "");
    expect(raw).toBe(LIVE_ENCODED);
    expect(routeForEventId(raw)).toEqual({ kind: "promoted", id: LIVE_ID });
  });
});

describe("eventIdForQuery never leaks the prefix", () => {
  it("strips promoted: and promoted%3A to the bare uuid", () => {
    expect(eventIdForQuery(LIVE_ENCODED)).toBe(LIVE_ID);
    expect(eventIdForQuery(LIVE_PREFIXED)).toBe(LIVE_ID);
    expect(eventIdForQuery(LIVE_ID)).toBe(LIVE_ID);
    expect(eventIdForQuery(LIVE_DOUBLE)).toBe(LIVE_ID);
  });

  it("refuses an empty or prefix-only id", () => {
    expect(eventIdForQuery("")).toBeNull();
    expect(eventIdForQuery(PROMOTED_ID_PREFIX)).toBeNull();
    expect(eventIdForQuery("promoted%3A")).toBeNull();
  });
});

describe("buildPromotedQuery never puts promoted%3A on event_id", () => {
  it("queries the bare uuid from every live-shaped input", () => {
    for (const raw of [LIVE_ENCODED, LIVE_PREFIXED, LIVE_ID, LIVE_DOUBLE]) {
      const q = buildPromotedQuery({ eventId: raw, anyStatus: true });
      expect(q).toContain(`event_id=eq.${LIVE_ID}`);
      expect(q).not.toContain("promoted%3A");
      expect(q).not.toContain("promoted:");
    }
  });
});
