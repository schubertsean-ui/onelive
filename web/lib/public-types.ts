// Public feed types — mirror the FastAPI contract in api/public.py EXACTLY.
// If the API shape changes, this file must change with it (no drift).

// The four honest confidence states from the pipeline. `disputed` is always
// rendered (never dropped); `unverified` is shown but visibly caveated. This
// union is the single source of truth for the UI's trust vocabulary.
export type Confidence = "confirmed" | "likely" | "unverified" | "disputed";

export const CONFIDENCE_VALUES: Confidence[] = [
  "confirmed",
  "likely",
  "unverified",
  "disputed",
];

export function isConfidence(v: unknown): v is Confidence {
  return typeof v === "string" && (CONFIDENCE_VALUES as string[]).includes(v);
}

// Shape returned by GET /tonight (see api/public.py::tonight).
export type TonightVenue = {
  venue_id: string | null;
  name: string | null;
  city: string | null;
};

export type TonightEvent = {
  event_id: string;
  start_time: string | null; // ISO 8601
  confidence: Confidence | string | null; // API may add states; UI degrades safely
  notes: string | null;
  venue: TonightVenue;
  artist_ids: string[];
};
