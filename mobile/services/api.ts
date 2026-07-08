const API_BASE = process.env.EXPO_PUBLIC_API || "http://localhost:8000";

export async function fetchTonight(city: string) {
  const res = await fetch(`${API_BASE}/tonight?city=${encodeURIComponent(city)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
