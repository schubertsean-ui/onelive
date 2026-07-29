"use client";

// Share card (group-plans P0 / brief §6.D5), browser half. The pure payload is
// built in lib/share.ts (unit-tested); this component just delivers it:
//   * Web Share API where the device has it (phones) -> the native OS sheet, so
//     "text this to a friend" is Messages/WhatsApp/etc. with one tap. This is
//     the whole point of P0 — the couple case, answered.
//   * Clipboard fallback where it doesn't (most desktops) -> copy text+link and
//     say so.
// No account, no server call, nothing stored — a share is a link, full stop
// (group-plans trust screen: utility, not network).

import { useEffect, useState } from "react";
import type { LicensedEvent } from "../../../../lib/licensed";
import { shareData, buildClipboardText } from "../../../../lib/share";

type Status = "idle" | "copied" | "error";

export default function ShareButton({ event }: { event: LicensedEvent }) {
  // Origin is only knowable in the browser; until we have it, the button still
  // renders but composes its link against the live origin at click time.
  const [origin, setOrigin] = useState("");
  const [status, setStatus] = useState<Status>("idle");

  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  async function onShare() {
    const here = origin || window.location.origin;
    const data = shareData(event, here);

    // Prefer the native sheet — it reaches the messaging apps a person already
    // texts friends in.
    const nav = typeof navigator !== "undefined" ? navigator : undefined;
    if (nav && typeof nav.share === "function") {
      try {
        await nav.share(data);
        return; // shared (or the sheet handled it); nothing more to say.
      } catch (err) {
        // A user who dismisses the sheet is not an error — do not fall through
        // to clipboard or flash a failure at them.
        if (err instanceof DOMException && err.name === "AbortError") return;
        // Any other share failure falls through to the copy path below.
      }
    }

    // Fallback: copy text + link so it can be pasted into any chat.
    try {
      const text = buildClipboardText(event, here);
      if (nav && nav.clipboard && typeof nav.clipboard.writeText === "function") {
        await nav.clipboard.writeText(text);
        setStatus("copied");
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  }

  // Reset the transient confirmation after a moment so the control returns to
  // its resting label.
  useEffect(() => {
    if (status === "idle") return;
    const t = setTimeout(() => setStatus("idle"), 2500);
    return () => clearTimeout(t);
  }, [status]);

  const label =
    status === "copied"
      ? "Link copied"
      : status === "error"
        ? "Couldn’t copy — long-press the link"
        : "Share";

  return (
    <button type="button" className="dshare" onClick={onShare}>
      <span aria-hidden="true">↗</span> {label}
      {/* Announce the copy result to assistive tech without moving focus. */}
      <span className="visually-hidden" role="status" aria-live="polite">
        {status === "copied" ? "Link copied to clipboard" : ""}
      </span>
    </button>
  );
}
