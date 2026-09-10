import type { LicensedEvent } from "./licensed";

function query(e: LicensedEvent): string | null {
  if (e.venue_lat != null && e.venue_lng != null) {
    return `${e.venue_lat},${e.venue_lng}`;
  }
  const text = [e.venue_name, e.venue_address, e.venue_city].filter(Boolean).join(", ");
  return text || null;
}

export function appleMapUrl(e: LicensedEvent): string | null {
  const q = query(e);
  return q ? `https://maps.apple.com/?q=${encodeURIComponent(q)}` : null;
}

export function googleMapUrl(e: LicensedEvent): string | null {
  const q = query(e);
  return q ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}` : null;
}

export type MapLinks = { apple: string | null; google: string | null };

/** Clickable maps. No picture here. Picture only when lat+lng already stored. */
export function mapLinks(e: LicensedEvent): MapLinks {
  return { apple: appleMapUrl(e), google: googleMapUrl(e) };
}

export function hasPrintedPoint(e: LicensedEvent): boolean {
  return e.venue_lat != null && e.venue_lng != null;
}
