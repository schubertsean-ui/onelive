import { apiGet } from "./api";
import { TonightEvent } from "./public-types";

// Fetch the "tonight" feed. Errors propagate to the caller so the UI can render
// an honest error state (we never swallow failures and show a fake-empty feed).
export async function fetchTonight(params?: {
  city?: string;
  hours?: number;
  limit?: number;
}): Promise<TonightEvent[]> {
  const q = new URLSearchParams();
  if (params?.city) q.set("city", params.city);
  if (params?.hours != null) q.set("hours", String(params.hours));
  if (params?.limit != null) q.set("limit", String(params.limit));
  const qs = q.toString();
  const data = await apiGet(`/tonight${qs ? `?${qs}` : ""}`);
  if (!Array.isArray(data)) {
    throw new Error("Unexpected response shape from /tonight");
  }
  return data as TonightEvent[];
}
