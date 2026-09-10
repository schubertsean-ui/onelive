"use client";

import type { LicensedEvent, SparkLine } from "../../../lib/licensed";
import { TwoRoomCard, type LensSide } from "./TwoRoomCard";
import { trustDisplay } from "../../../lib/trust";
import { detailProviderLabel, detailTrustKind } from "../../../lib/detail";

export function SparkLineView({ spark, artist }: { spark?: SparkLine | null; artist: string }) {
  if (!spark || !spark.text) return null;
  const aiDrafted = spark.tier === "C";
  if (!aiDrafted) {
    return (
      <span className="spark">
        <span className="sparktext">{spark.text}</span>
        {spark.attribution ? <span className="sparkattr"> — {spark.attribution}</span> : null}
      </span>
    );
  }
  return (
    <details className="spark ai sparkdisc">
      <summary aria-label={`${spark.text} — AI-drafted line, tap for what that means`}>
        <span className="sparktext">{spark.text}</span>
        <span className="sparkmark" aria-hidden="true">{" ✳"}</span>
        {spark.attribution ? <span className="sparkattr"> — {spark.attribution}</span> : null}
      </summary>
      <span className="sparksheet" role="note">
        Drafted from {artist}&rsquo;s own materials.
      </span>
    </details>
  );
}

function trustFor(e: LicensedEvent) {
  return trustDisplay(e.confidence, detailProviderLabel(e), detailTrustKind(e));
}

export function TrustMark({ e }: { e: LicensedEvent }) {
  const t = trustFor(e);
  if (!t.surface || !t.marker) return null;
  return <span className={`cau${t.disputed ? " disp" : ""}`} title={t.sheet}>{t.marker}</span>;
}

function headline(e: LicensedEvent): string {
  return e.performer && e.performer.length <= 80 ? e.performer : e.title;
}

/** The only list card. Old RichCard body is gone. */
export function FeedCard({
  e,
  onNow,
  onOpen,
}: {
  e: LicensedEvent;
  onNow: boolean;
  onOpen: (e: LicensedEvent, side: LensSide) => void;
}) {
  return (
    <TwoRoomCard
      e={e}
      onNow={onNow}
      onOpen={onOpen}
      sparkView={<SparkLineView spark={e.spark} artist={headline(e)} />}
      trustMark={<TrustMark e={e} />}
    />
  );
}
