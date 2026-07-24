// Ops-console backend client — the ONLY link between the web app and the
// FastAPI service (candidate review / gating / evidence). It is deliberately
// isolated here and named for what it is: nothing on the consumer feed imports
// this module. The consumer surface reads Supabase directly (lib/licensed.ts),
// so the FastAPI backend being undeployed can never break the consumer build.
//
// Every page that calls this MUST be `export const dynamic = "force-dynamic"`
// so the client is hit at request time, never during the static build.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function apiPost(path: string, body: any) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
