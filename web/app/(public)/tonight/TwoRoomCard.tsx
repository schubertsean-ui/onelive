"use client";

import type { ReactNode } from "react";
import type { LicensedEvent } from "../../../lib/licensed";
import {
  LOOKING_FOR_MORE,
  kindChip,
  lookingForMore,
  detailsThin,
  venueAreaLabel,
  venueSiteHost,
  printablePlace,
} from "../../../lib/cardSlots";
import { detailPrice as fmtPrice, httpOrNull as httpUrl, sourceCredit } from "../../../lib/detail";
import { contextualPreview } from "../../../lib/preview";

const TZ = "America/Chicago";

function fmtWhen(iso: string | null): string {
  if (!iso) return "Date TBA";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Date TBA";
  return d.toLocaleString("en-US", {
    timeZone: TZ,
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function headline(e: LicensedEvent): string {
  return e.performer && e.performer.length <= 80 ? e.performer : e.title;
}

export type LensSide = "artist" | "venue";

export function TwoRoomCard({
  e,
  onNow,
  onOpen,
  sparkView,
  trustMark,
}: {
  e: LicensedEvent;
  onNow: boolean;
  onOpen: (e: LicensedEvent, side: LensSide) => void;
  sparkView: ReactNode;
  trustMark: ReactNode;
}) {
  const price = fmtPrice(e);
  const img = httpUrl(e.image_url);
  const preview = contextualPreview(e);
  const credit = sourceCredit(e);
  const chip = kindChip(e);
  const area = venueAreaLabel(e);
  const host = venueSiteHost(e.venue_url);
  const street = (e.venue_address ?? "").trim();
  const place = printablePlace(e);
  const needMore = lookingForMore(e);
  const thin = detailsThin(e);
  return (
    <article className="room">
      <div className="rooms">
        <div className="zone z-artist">
          <button
            type="button"
            className="zdoor"
            onClick={() => onOpen(e, "artist")}
            aria-label={`${headline(e)}${e.spark ? ` — ${e.spark.text}` : ""} — open artist details${preview ? ` and ${preview.label.toLowerCase()}` : ""}`}
          />
          {img ? <div className="rph" style={{ backgroundImage: `url(${img})` }} aria-hidden /> : null}
          <span className="who">{headline(e)}</span>
          <div className="rtime">
            <span className="when">{fmtWhen(e.start_time)}</span>
            {onNow ? <span className="onnow">on now</span> : null}
            <span className={`pr${price.free ? " free" : ""}`}>{price.text}</span>
            {trustMark}
          </div>
          {sparkView}
          {preview ? (
            <div className="hookrow">
              <span className="hook">{preview.label}</span>
              {preview.links.map((l) => (
                <a
                  key={l.service}
                  className="hchip"
                  href={l.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {l.service}
                </a>
              ))}
            </div>
          ) : null}
          {chip ? <span className="kchip">{chip}</span> : null}
          <span className="go" aria-hidden="true">artist ›</span>
        </div>
        <button
          type="button"
          className="zone z-venue"
          onClick={() => onOpen(e, "venue")}
          aria-label={`${place ?? "Venue"} — open venue details`}
        >
          {place ? <span className="vname">{place}</span> : <span className="vname vhole">Place to be confirmed</span>}
          {area ? <span className="mmap">{area}</span> : null}
          {street ? <span className="vaddr">{street}</span> : null}
          {host ? <span className="vsite">{host}</span> : null}
          <span className="go" aria-hidden="true">venue ›</span>
        </button>
      </div>
      {thin ? (
        <details className="qdisc">
          <summary aria-label="Details may be thin">?</summary>
          <span className="qsheet" role="note">
            Details may change. Check or call the site, artist, or organizer.
          </span>
        </details>
      ) : null}
      {needMore ? <p className="needmore">{LOOKING_FOR_MORE}</p> : null}
      {credit.generic ? null : <p className="rsrc">via {credit.name}</p>}
    </article>
  );
}
