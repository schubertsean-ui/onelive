// Minimal mock of the FastAPI /tonight endpoint for local UI QA only.
// Serves representative data covering all four confidence states, plus
// switchable modes (empty, error) via env for state QA.
import { createServer } from "node:http";

const MODE = process.env.MOCK_MODE || "full"; // full | empty | error
const now = new Date();
const at = (h, m = 0) => {
  const d = new Date(now);
  d.setHours(h, m, 0, 0);
  return d.toISOString();
};

const FULL = [
  {
    event_id: "e1", start_time: at(20, 0), confidence: "confirmed",
    notes: "Doors 7pm. Two sets from the resident trio.",
    venue: { venue_id: "v1", name: "The Continental Club", city: "Austin" }, artist_ids: [],
  },
  {
    event_id: "e2", start_time: at(20, 30), confidence: "likely",
    notes: "Listed on the venue calendar; ticket link pending.",
    venue: { venue_id: "v2", name: "Antone's Nightclub", city: "Austin" }, artist_ids: [],
  },
  {
    event_id: "e3", start_time: at(21, 0), confidence: "unverified",
    notes: "Single social post only — details may change.",
    venue: { venue_id: "v3", name: "Sam's Town Point", city: "Austin" }, artist_ids: [],
  },
  {
    event_id: "e4", start_time: at(21, 30), confidence: "disputed",
    notes: "One source lists tonight, another lists tomorrow.",
    venue: { venue_id: "v4", name: "Hole in the Wall", city: "Austin" }, artist_ids: [],
  },
  {
    event_id: "e5", start_time: at(22, 0), confidence: null,
    notes: "State missing from feed — shown cautiously.",
    venue: { venue_id: "v5", name: "Mohawk", city: "Austin" }, artist_ids: [],
  },
  {
    event_id: "e6", start_time: null, confidence: "confirmed",
    notes: null,
    venue: { venue_id: null, name: null, city: null }, artist_ids: [],
  },
];

const server = createServer((req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (!req.url.startsWith("/tonight")) {
    res.writeHead(404).end("[]");
    return;
  }
  if (MODE === "error") {
    res.writeHead(500).end("boom");
    return;
  }
  const body = MODE === "empty" ? [] : FULL;
  res.writeHead(200, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
});

const port = Number(process.env.MOCK_PORT || 8000);
server.listen(port, () => console.log(`mock /tonight (${MODE}) on :${port}`));
