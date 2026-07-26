import { useState } from "react";

/* =====================================================================
   ⚠ HISTORICAL REFERENCE — DO NOT COPY THE TRUST LINE. This prototype
   predates the ratified trust-display rules (brief v2.4 §2): the
   "✓ Confirmed by multiple sources" TrustLine below is now FORBIDDEN
   (no badges, no "confirmed" text, ever). Confidence is expressed only
   as the quiet-icon + dismissible-sheet pattern. Kept verbatim below
   for wireframe/layout reference only. Delta logged per the charter
   rule "deltas from the brief are logged, never silent" (evaluator
   finding, PR #11 round 1).
   =====================================================================
   ONE LIVE — /tonight PROTOTYPE v2 · built from the founder's OWN
   wireframe & PRD (One_Live_1100.pdf, "V1 Fan-First, Zero Noise,
   Utility Wins") — nothing invented:
   · Home = "Tonight in Austin", chronological, genre markers,
     Free/Ticketed, "Hear it" inline preview, no login
   · Date tabs: Today / Tomorrow / This Week
   · Slide-in Filters: 8 genres, Free/Ticketed, venue search,
     neighborhoods (Downtown / East Austin / South Austin)
   · Event Detail: player, date, exact start, duration, venue+address,
     map link, parking, ticket link, add-to-calendar, share
   · Trust copy: "Info may change", "Time TBD", "Something off?"
   PALETTE (researched, founder brief: distinctive · fun · trustworthy):
   P1 "Indigo Stage" (RECOMMENDED) — blue-dark base (blue→trust/
   competence: Labrecque & Milne 2012, JAMS; Trustworthy-Blue study),
   near-black immersion per best-in-class music UI (Spotify #121212
   family), hot coral accent for energy (warm hues→excitement, same
   research). Two alternates included for founder confirmation.
   ===================================================================== */

const FONTS = `@import url('https://fonts.googleapis.com/css2?family=Unbounded:wght@600;800&family=Archivo:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;700&display=swap');`;

const PALETTES = {
  indigo: {
    label: "P1 · Indigo Stage (recommended)",
    why: "Blue-dark base = trust/competence (Labrecque & Milne 2012); dark immersion = music-UI best practice (Spotify); coral = fun/energy.",
    bg: "#0D1120", surface: "#161C30", surface2: "#1D2440", line: "#2A3354",
    ink: "#F0F3FB", dim: "#98A3C4", accent: "#FF6B4A", trust: "#57B8FF", free: "#3DDC97",
  },
  violet: {
    label: "P2 · Violet Hour",
    why: "Maximum distinctiveness; chartreuse accent is high-energy but carries weaker trust association in the literature.",
    bg: "#120F1E", surface: "#1B1730", surface2: "#241E40", line: "#332B57",
    ink: "#F4F1FB", dim: "#A49BC7", accent: "#D6FF4B", trust: "#8FB8FF", free: "#5EE6B0",
  },
  daylight: {
    label: "P3 · Daylight",
    why: "Light control option — strongest for daytime planning; weakest night-out atmosphere.",
    bg: "#F2F4F8", surface: "#FFFFFF", surface2: "#E7EBF3", line: "#D3DAE8",
    ink: "#141A2B", dim: "#5B6786", accent: "#E5482B", trust: "#1D6FD6", free: "#0E8A63",
  },
};

/* Copy: VERBATIM from founder docs is default; ALT are Claude suggestions, clearly flagged */
const COPY = {
  // No tagline on any product surface (brief §3, founder-ratified 2026-07-26:
  // "Use the new description for the tagline. Remove the old."). The masthead
  // carries the city and the date only. The former "Less chaos. Real shows." and
  // every alt tagline are removed so nothing copies a retired string out of this
  // reference. Framing that replaces it: "finding and engaging in experiences,
  // helping individuals and the culture thrive" — expressed through the design,
  // not printed as a slogan.
  verbatim: { h1: "Tonight in Austin", hear: "Hear it", unverified: "Info may change", tbd: "Time TBD", off: "Something off?" },
  alt: { h1: "Austin, tonight.", hear: "Play a taste", unverified: "Not yet confirmed", tbd: "Start time coming", off: "Report an issue" },
};

const GENRES = ["Rock", "Hip-Hop", "Jazz", "Electronic", "Country", "Metal", "Experimental", "Latin"];
const HOODS = ["Downtown", "East Austin", "South Austin"];

const EVENTS = [
  { id: 1, time: "7:30 PM", sort: 1930, artists: ["Grupo Maravilla"], genres: ["Latin"], venue: "Coral Snake", hood: "East Austin", address: "910 E 6th St", ticket: "Free", duration: "90 min", parking: "Street after 6 PM", conf: "confirmed" },
  { id: 2, time: "8:00 PM", sort: 2000, artists: ["Duel", "Witchcryer"], genres: ["Metal"], venue: "Valhalla", hood: "Downtown", address: "710 Red River St", ticket: "$15", duration: "3 sets", parking: "Garage on 7th", conf: "confirmed" },
  { id: 3, time: "8:30 PM", sort: 2030, artists: ["Ephraim Owens Quartet"], genres: ["Jazz"], venue: "The Elephant Room", hood: "Downtown", address: "315 Congress Ave", ticket: "$10", duration: "2 sets", parking: "Congress garages", conf: "confirmed" },
  { id: 4, time: "9:00 PM", sort: 2100, artists: ["Blk Odyssy"], genres: ["Hip-Hop"], venue: "Empire Control Room", hood: "Downtown", address: "606 E 7th St", ticket: "$20", duration: "75 min", parking: "Lot across street", conf: "confirmed" },
  { id: 5, time: "9:00 PM", sort: 2101, artists: ["Being Dead"], genres: ["Rock", "Experimental"], venue: "Hotel Vegas", hood: "East Austin", address: "1502 E 6th St", ticket: "$12", duration: "60 min", parking: "Limited — rideshare", conf: "unverified" },
  { id: 6, time: "9:30 PM", sort: 2130, artists: ["Croy & the Boys"], genres: ["Country"], venue: "Sagebrush", hood: "South Austin", address: "5500 S Congress Ave", ticket: "Free", duration: "2 hrs", parking: "On-site lot", conf: "confirmed" },
  { id: 7, time: "10:00 PM", sort: 2200, artists: ["Flora & Fawna"], genres: ["Electronic"], venue: "Kingdom", hood: "Downtown", address: "503 Brushy St", ticket: "$18", duration: "Open-late", parking: "Street + garage", conf: "confirmed" },
  { id: 8, time: "TBD", sort: 9999, artists: ["Late-Night Jazz Hang"], genres: ["Jazz", "Experimental"], venue: "Monks Jazz Club", hood: "East Austin", address: "2331 E Cesar Chavez", ticket: "$10", duration: "—", parking: "Street", conf: "tbd" },
];

const t = (obj) => ({ fontFamily: obj });

export default function OneLiveTonight() {
  const [pal, setPal] = useState("indigo");
  const [copyMode, setCopyMode] = useState("verbatim");
  const [view, setView] = useState("feed"); // feed | detail
  const [ev, setEv] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [dateTab, setDateTab] = useState("Today");
  const [gSel, setGSel] = useState([]);
  const [show, setShow] = useState("All"); // All | Free | Ticketed
  const [vq, setVq] = useState("");
  const [hSel, setHSel] = useState([]);
  const [playing, setPlaying] = useState(null);

  const P = PALETTES[pal];
  const C = COPY[copyMode];

  const toggle = (arr, set, v) => set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  const filtered = EVENTS.filter((e) =>
    (gSel.length === 0 || e.genres.some((g) => gSel.includes(g))) &&
    (show === "All" || (show === "Free" ? e.ticket === "Free" : e.ticket !== "Free")) &&
    (vq === "" || e.venue.toLowerCase().includes(vq.toLowerCase())) &&
    (hSel.length === 0 || hSel.includes(e.hood))
  ).sort((a, b) => a.sort - b.sort);

  const activeFilters = gSel.length + (show !== "All" ? 1 : 0) + (vq ? 1 : 0) + hSel.length;

  const chip = (active) => ({
    ...t("'Space Grotesk', monospace"), fontSize: 13, minHeight: 44, padding: "8px 14px",
    borderRadius: 999, cursor: "pointer",
    border: `1px solid ${active ? P.accent : P.line}`,
    background: active ? P.accent + "26" : "transparent",
    color: active ? P.accent : P.dim,
  });

  const TrustLine = ({ e, big }) =>
    e.conf === "confirmed" ? (
      <span style={{ ...t("'Space Grotesk', monospace"), color: P.trust, fontSize: big ? 13 : 11 }}>✓ Confirmed by multiple sources</span>
    ) : (
      <span style={{ ...t("'Space Grotesk', monospace"), color: P.accent, fontSize: big ? 13 : 11 }}>
        {e.conf === "tbd" ? C.tbd : C.unverified}
      </span>
    );

  /* ---------------- EVENT DETAIL (per PRD §4.5) ---------------- */
  if (view === "detail" && ev) {
    return (
      <div style={{ background: P.bg, minHeight: "100vh", color: P.ink }}>
        <style>{FONTS}</style>
        <div style={{ maxWidth: 560, margin: "0 auto", padding: "16px 16px 48px" }}>
          <button onClick={() => setView("feed")} style={{ ...chip(false), marginBottom: 14 }}>← Back to tonight</button>

          <div style={{ ...t("'Space Grotesk', monospace"), color: P.accent, fontSize: 13 }}>{ev.time} · {dateTab === "Today" ? "Sat Jul 12" : dateTab}</div>
          <h1 style={{ ...t("'Unbounded', sans-serif"), fontWeight: 800, fontSize: 30, lineHeight: 1.1, margin: "6px 0 4px" }}>{ev.artists.join(" + ")}</h1>
          <div style={{ marginBottom: 6 }}><TrustLine e={ev} big /></div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
            {ev.genres.map((g) => (
              <span key={g} style={{ ...t("'Space Grotesk', monospace"), fontSize: 12, color: P.dim, border: `1px solid ${P.line}`, borderRadius: 6, padding: "2px 8px" }}>{g}</span>
            ))}
            <span style={{ ...t("'Space Grotesk', monospace"), fontSize: 12, color: ev.ticket === "Free" ? P.free : P.ink, border: `1px solid ${P.line}`, borderRadius: 6, padding: "2px 8px" }}>{ev.ticket}</span>
          </div>

          {/* Embedded player — PRD: loads without redirect */}
          <div style={{ background: P.surface, border: `1px solid ${P.line}`, borderRadius: 14, padding: 16, display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
            <button onClick={() => setPlaying(playing === ev.id ? null : ev.id)} aria-label="Play preview"
              style={{ width: 52, height: 52, borderRadius: "50%", border: "none", cursor: "pointer", background: P.accent, color: P.bg, fontSize: 20, fontWeight: 700 }}>
              {playing === ev.id ? "❚❚" : "▶"}
            </button>
            <div>
              <div style={{ ...t("'Archivo', sans-serif"), fontWeight: 600, fontSize: 14 }}>{playing === ev.id ? "Previewing…" : C.hear}</div>
              <div style={{ ...t("'Space Grotesk', monospace"), fontSize: 12, color: P.dim }}>Spotify · SoundCloud · Bandcamp · YouTube</div>
            </div>
            <div style={{ marginLeft: "auto", display: "flex", gap: 3, alignItems: "flex-end", height: 26 }}>
              {[10, 18, 8, 22, 14, 24, 9, 16].map((h, i) => (
                <div key={i} style={{ width: 4, height: playing === ev.id ? h : 6, background: P.accent, borderRadius: 2, transition: "height .3s" }} />
              ))}
            </div>
          </div>

          {/* Logistics block — every PRD-required field */}
          <div style={{ background: P.surface, border: `1px solid ${P.line}`, borderRadius: 14, padding: 16, marginBottom: 16 }}>
            {[
              ["When", `${dateTab === "Today" ? "Tonight" : dateTab} · ${ev.time} · ${ev.duration}`],
              ["Venue", `${ev.venue} — ${ev.address}`],
              ["Neighborhood", ev.hood],
              ["Parking", ev.parking],
            ].map(([k, v]) => (
              <div key={k} style={{ display: "flex", gap: 12, padding: "7px 0", borderBottom: `1px solid ${P.line}` }}>
                <div style={{ ...t("'Space Grotesk', monospace"), fontSize: 12, color: P.dim, minWidth: 104, textTransform: "uppercase", letterSpacing: 1 }}>{k}</div>
                <div style={{ ...t("'Archivo', sans-serif"), fontSize: 14 }}>{v}</div>
              </div>
            ))}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              <button style={chip(true)}>Get tickets ↗</button>
              <button style={chip(false)}>Map</button>
              <button style={chip(false)}>Add to calendar</button>
              <button style={chip(false)}>Share</button>
            </div>
          </div>

          <button style={{ ...t("'Space Grotesk', monospace"), background: "none", border: "none", color: P.dim, fontSize: 13, textDecoration: "underline", cursor: "pointer", minHeight: 44 }}>{C.off}</button>
        </div>
      </div>
    );
  }

  /* ---------------- FEED (PRD §4.1–4.4) ---------------- */
  return (
    <div style={{ background: P.bg, minHeight: "100vh", color: P.ink }}>
      <style>{FONTS}</style>
      <style>{`button:focus-visible,input:focus-visible{outline:2px solid ${P.accent};outline-offset:2px} @media (prefers-reduced-motion:reduce){*{transition:none!important}}`}</style>

      <div style={{ maxWidth: 560, margin: "0 auto", padding: "16px 16px 48px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ ...t("'Unbounded', sans-serif"), fontWeight: 800, fontSize: 14, letterSpacing: 2 }}>
            ONE<span style={{ color: P.accent }}> LIVE</span>
          </div>
        </div>
        <h1 style={{ ...t("'Unbounded', sans-serif"), fontWeight: 800, fontSize: 32, lineHeight: 1.08, margin: "14px 0 4px" }}>{C.h1}</h1>
        <div style={{ ...t("'Archivo', sans-serif"), color: P.dim, fontSize: 13, marginBottom: 14 }}>
          {filtered.length} shows · chronological · no pay-to-rank
        </div>

        {/* Date tabs (PRD §4.2) + Filters trigger */}
        <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
          {["Today", "Tomorrow", "This Week"].map((d) => (
            <button key={d} onClick={() => setDateTab(d)} style={chip(dateTab === d)}>{d}</button>
          ))}
          <button onClick={() => setFiltersOpen(true)} style={{ ...chip(activeFilters > 0), marginLeft: "auto" }}>
            Filters{activeFilters > 0 ? ` · ${activeFilters}` : ""}
          </button>
        </div>

        {/* Feed */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filtered.map((e) => (
            <div key={e.id} role="button" tabIndex={0} onClick={() => { setEv(e); setView("detail"); }}
              onKeyDown={(k) => k.key === "Enter" && (setEv(e), setView("detail"))}
              style={{ background: P.surface, border: `1px solid ${P.line}`, borderRadius: 14, padding: 14, display: "flex", gap: 12, cursor: "pointer" }}>
              <div style={{ ...t("'Space Grotesk', monospace"), color: e.conf === "tbd" ? P.dim : P.accent, fontWeight: 700, fontSize: 15, minWidth: 72, paddingTop: 2 }}>{e.time}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ ...t("'Archivo', sans-serif"), fontWeight: 700, fontSize: 17, lineHeight: 1.25 }}>{e.artists.join(" + ")}</div>
                <div style={{ ...t("'Archivo', sans-serif"), color: P.dim, fontSize: 13, margin: "3px 0 2px" }}>{e.venue} · {e.hood}</div>
                <TrustLine e={e} />
                <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap", alignItems: "center" }}>
                  {e.genres.map((g) => (
                    <span key={g} style={{ ...t("'Space Grotesk', monospace"), fontSize: 11, color: P.dim, border: `1px solid ${P.line}`, borderRadius: 6, padding: "2px 7px" }}>{g}</span>
                  ))}
                  <span style={{ ...t("'Space Grotesk', monospace"), fontSize: 11, color: e.ticket === "Free" ? P.free : P.ink, border: `1px solid ${P.line}`, borderRadius: 6, padding: "2px 7px" }}>{e.ticket}</span>
                  <button onClick={(k) => { k.stopPropagation(); setPlaying(playing === e.id ? null : e.id); }}
                    style={{ marginLeft: "auto", ...t("'Space Grotesk', monospace"), fontSize: 12, fontWeight: 700, minHeight: 36, padding: "6px 12px", borderRadius: 999, border: "none", cursor: "pointer", background: playing === e.id ? P.ink : P.accent, color: P.bg }}>
                    {playing === e.id ? "❚❚ Playing" : `▶ ${C.hear}`}
                  </button>
                </div>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div style={{ ...t("'Archivo', sans-serif"), color: P.dim, background: P.surface, border: `1px dashed ${P.line}`, borderRadius: 14, padding: 24, textAlign: "center" }}>
              No shows match these filters. Clear a filter to see more of tonight.
            </div>
          )}
        </div>

        {/* Design-review strip (co-design only; removed in production) */}
        <div style={{ marginTop: 24, background: P.surface2, border: `1px solid ${P.line}`, borderRadius: 14, padding: 14 }}>
          <div style={{ ...t("'Space Grotesk', monospace"), fontSize: 11, color: P.dim, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Co-design controls (not shipped)</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
            {Object.keys(PALETTES).map((k) => (
              <button key={k} onClick={() => setPal(k)} style={chip(pal === k)}>{PALETTES[k].label}</button>
            ))}
          </div>
          <div style={{ ...t("'Archivo', sans-serif"), fontSize: 11, color: P.dim, marginBottom: 10 }}>{P.why}</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button onClick={() => setCopyMode("verbatim")} style={chip(copyMode === "verbatim")}>Copy: your verbatim</button>
            <button onClick={() => setCopyMode("alt")} style={chip(copyMode === "alt")}>Copy: Claude alts (suggestions)</button>
          </div>
        </div>
      </div>

      {/* Slide-in Filter panel (PRD §4.3, exact filter set) */}
      {filtersOpen && (
        <div onClick={() => setFiltersOpen(false)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)" }}>
          <div onClick={(k) => k.stopPropagation()} style={{ position: "absolute", right: 0, top: 0, bottom: 0, width: "min(340px, 88vw)", background: P.surface, borderLeft: `1px solid ${P.line}`, padding: 18, overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div style={{ ...t("'Unbounded', sans-serif"), fontWeight: 800, fontSize: 16 }}>Filters</div>
              <button onClick={() => setFiltersOpen(false)} style={chip(false)}>Done</button>
            </div>

            <div style={{ ...t("'Space Grotesk', monospace"), fontSize: 11, color: P.dim, textTransform: "uppercase", letterSpacing: 1, margin: "10px 0 8px" }}>Genre</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {GENRES.map((g) => (
                <button key={g} onClick={() => toggle(gSel, setGSel, g)} style={chip(gSel.includes(g))}>{g}</button>
              ))}
            </div>

            <div style={{ ...t("'Space Grotesk', monospace"), fontSize: 11, color: P.dim, textTransform: "uppercase", letterSpacing: 1, margin: "16px 0 8px" }}>Show type</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {["All", "Free", "Ticketed"].map((s) => (
                <button key={s} onClick={() => setShow(s)} style={chip(show === s)}>{s}</button>
              ))}
            </div>

            <div style={{ ...t("'Space Grotesk', monospace"), fontSize: 11, color: P.dim, textTransform: "uppercase", letterSpacing: 1, margin: "16px 0 8px" }}>Venue</div>
            <input value={vq} onChange={(e) => setVq(e.target.value)} placeholder="Search venues…"
              style={{ ...t("'Archivo', sans-serif"), width: "100%", boxSizing: "border-box", background: P.bg, border: `1px solid ${P.line}`, color: P.ink, borderRadius: 10, padding: 12, fontSize: 14 }} />

            <div style={{ ...t("'Space Grotesk', monospace"), fontSize: 11, color: P.dim, textTransform: "uppercase", letterSpacing: 1, margin: "16px 0 8px" }}>Neighborhood</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {HOODS.map((h) => (
                <button key={h} onClick={() => toggle(hSel, setHSel, h)} style={chip(hSel.includes(h))}>{h}</button>
              ))}
            </div>

            {activeFilters > 0 && (
              <button onClick={() => { setGSel([]); setShow("All"); setVq(""); setHSel([]); }}
                style={{ ...chip(false), marginTop: 18, width: "100%" }}>Clear all filters</button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
