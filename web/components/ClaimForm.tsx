"use client";
import { useState } from "react";
import { apiPost } from "../lib/ops-api";

// The class-D door, opening inward. A venue whose listings live behind a login
// is not out of scope — it is out of reach, and this is the invitation.
//
// The form deliberately offers no way to set the class or the confidence: who
// hands the listings over decides the class (organizer -> E, someone reporting
// on their behalf -> F), and every claim is recorded `unverified` until a
// person confirms this contact speaks for this venue. See worker/claim/intake.py.

type Receipt = {
  // INTERNAL receipt (founder rule 2026-09-01): received / held / not live.
  // This surface is for an operator; it is never evidence to show a venue, and
  // it must never read as "we have your calendar" or "you are on 1Live".
  status: string[];
  source_id: string;
  venue_name: string;
  coverage_class: string;
  source_class: string;
  confidence: string;
  intake_mode: string;
  forward_to: string;
  listings_recorded: number;
  hold_reason: string;
};

// A refusal and a PARTIAL failure are NOT the same state and must not read the
// same (evaluator finding, PR #203). Every error used to render as "Refused —
// nothing was recorded", which is false on the API's PARTIAL path: there the
// source row and some listings ARE committed. Telling an operator the catalog is
// clean when rows were written is a trust display defect — they would retry, or
// tell a venue the wrong thing. The API marks that path with a leading
// "PARTIAL:", which is the one thing this branch keys on.
function isPartial(detail: string): boolean {
  return detail.trimStart().startsWith("PARTIAL:");
}

// The API refuses with a message written for the venue owner to read (422 +
// {"detail": "..."}), and `apiPost` surfaces the raw response body. Showing that
// body verbatim would put the sentence behind JSON braces and \u-escapes — the
// one place a person most needs plain language. Pull the detail out; fall back
// to the raw text if the body is not the shape we expect, so a refusal is never
// swallowed into a generic message.
function refusalText(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.detail === "string") return parsed.detail;
  } catch {
    // Not JSON — the raw text is the best thing we have.
  }
  return raw;
}

const MODES: { id: string; label: string; help: string }[] = [
  {
    id: "ics_url",
    label: "Calendar feed URL",
    help: "Paste the address of the venue's own calendar feed (.ics or a public calendar link). We never fetch it until the claim is verified, and we never accept a sign-in page or a URL with a password in it.",
  },
  {
    id: "csv_upload",
    label: "Spreadsheet (CSV)",
    help: "Paste or upload the listings. Required columns: title, start. Optional: end, venue, city, url, notes. If any row is unreadable the whole file is refused — nothing is half-recorded.",
  },
  {
    id: "email_forward",
    label: "Email the listings",
    help: "The organizer forwards their listings to the intake address. Recording this registers the venue so the forwarded mail has somewhere to land.",
  },
];

export function ClaimForm({ forwardTo }: { forwardTo: string }) {
  const [venueName, setVenueName] = useState("");
  const [role, setRole] = useState("organizer");
  const [mode, setMode] = useState("ics_url");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [feedUrl, setFeedUrl] = useState("");
  const [csvText, setCsvText] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<Receipt | null>(null);

  const coverageClass = role === "organizer" ? "E (first party)" : "F (human report)";
  const activeMode = MODES.find((m) => m.id === mode) ?? MODES[0];

  async function readCsvFile(file: File) {
    setCsvText(await file.text());
  }

  async function submit() {
    setBusy(true);
    setError("");
    setReceipt(null);
    try {
      const body = await apiPost("/ops/claims", {
        venue_name: venueName,
        submitter_role: role,
        intake_mode: mode,
        contact_name: contactName,
        contact_email: contactEmail,
        feed_url: feedUrl,
        csv_text: csvText,
        notes,
      });
      setReceipt(body as Receipt);
    } catch (e: unknown) {
      // The API's refusal text is written for the venue owner to read, so it is
      // shown verbatim rather than replaced with a generic failure message.
      setError(refusalText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="h1">Record a venue claim</div>
      <p className="small">
        For an organizer whose listings sit behind a login, a paywall, or a bot wall. We
        do not fetch those — the organizer hands the listings over instead. Recorded as
        class {coverageClass} at confidence <strong>unverified</strong>, and held —
        <strong> not live</strong> — until a person verifies the contact.
      </p>

      <div className="row" style={{ marginTop: 12 }}>
        <label style={{ flex: "1 1 260px" }}>
          <span className="small">Venue / organizer name</span>
          <input
            className="input"
            value={venueName}
            onChange={(e) => setVenueName(e.target.value)}
            placeholder="Mohawk Austin"
          />
        </label>
        <label style={{ flex: "1 1 200px" }}>
          <span className="small">Who is handing this over?</span>
          <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="organizer">The organizer themselves — class E</option>
            <option value="third_party">Someone reporting it — class F</option>
          </select>
        </label>
      </div>

      <div className="row" style={{ marginTop: 12 }}>
        <label style={{ flex: "1 1 260px" }}>
          <span className="small">Contact name</span>
          <input className="input" value={contactName} onChange={(e) => setContactName(e.target.value)} />
        </label>
        <label style={{ flex: "1 1 260px" }}>
          <span className="small">Contact email</span>
          <input className="input" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
        </label>
      </div>

      <div style={{ marginTop: 16 }}>
        <span className="small">How the listings reach us</span>
        <div className="row" style={{ marginTop: 6 }}>
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              className={m.id === mode ? "btn btnPrimary" : "btn"}
              aria-pressed={m.id === mode}
              onClick={() => setMode(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="small" style={{ marginTop: 8 }}>{activeMode.help}</p>
      </div>

      {mode === "ics_url" && (
        <div style={{ marginTop: 12 }}>
          <input
            className="input"
            value={feedUrl}
            onChange={(e) => setFeedUrl(e.target.value)}
            placeholder="https://example.com/events.ics"
            aria-label="Calendar feed URL"
          />
        </div>
      )}

      {mode === "csv_upload" && (
        <div style={{ marginTop: 12 }}>
          <input
            type="file"
            accept=".csv,text/csv"
            aria-label="Upload CSV of listings"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void readCsvFile(file);
            }}
          />
          <textarea
            className="input"
            style={{ marginTop: 8, fontFamily: "monospace" }}
            rows={6}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            placeholder={"title,start,end,venue,city,url\nDoom Jazz Night,2026-09-12T21:00:00-05:00,,Mohawk,Austin,https://example.com/doom"}
            aria-label="CSV listings"
          />
        </div>
      )}

      {mode === "email_forward" && (
        <p className="small" style={{ marginTop: 12 }}>
          {forwardTo.includes("@") ? (
            <>
              Ask the organizer to forward their listings to <strong>{forwardTo}</strong>.
              Recording the claim registers the venue; the forwarded mail is parsed later
              under the same gates as everything else.
            </>
          ) : (
            <>
              <strong>No intake mailbox is configured</strong>, so this route is closed
              and recording will be refused — there is no address to give an organizer.
              Set <code>ONELIVE_LISTINGS_INTAKE_EMAIL</code> to a mailbox someone reads,
              or use the calendar-feed or CSV route.
            </>
          )}
        </p>
      )}

      <div style={{ marginTop: 12 }}>
        <textarea
          className="input"
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Notes (how we reached them, what they said)"
          aria-label="Notes"
        />
      </div>

      <div style={{ marginTop: 12 }}>
        <button className="btn btnPrimary" onClick={submit} disabled={busy || !venueName}>
          {busy ? "Recording…" : "Record claim"}
        </button>
      </div>

      {error && (
        isPartial(error) ? (
          <p className="small" role="alert" style={{ marginTop: 12, color: "#a11" }}>
            <strong>Partially recorded — the catalog changed.</strong> {error}
          </p>
        ) : (
          <p className="small" role="alert" style={{ marginTop: 12, color: "#a11" }}>
            Refused — nothing was recorded. {error}
          </p>
        )
      )}

      {receipt && (
        <div className="card" style={{ marginTop: 12 }} role="status">
          <div className="h1" style={{ fontSize: 16 }}>
            {(receipt.status ?? []).join(" · ") || "received · held · not live"}
          </div>
          <p className="small" style={{ marginTop: -6, marginBottom: 10 }}>
            Internal receipt. Not a standing to quote back to the venue.
          </p>
          <table className="table">
            <tbody>
              <tr><th>Venue</th><td>{receipt.venue_name}</td></tr>
              <tr><th>Coverage class</th><td>{receipt.coverage_class}</td></tr>
              <tr><th>Source class</th><td>{receipt.source_class}</td></tr>
              <tr><th>Confidence</th><td>{receipt.confidence}</td></tr>
              <tr><th>Listings recorded</th><td>{receipt.listings_recorded}</td></tr>
              <tr><th>Source id</th><td>{receipt.source_id}</td></tr>
            </tbody>
          </table>
          <p className="small" style={{ marginTop: 8 }}>{receipt.hold_reason}</p>
        </div>
      )}
    </div>
  );
}
