// Stealth-launch email allowlist (web gate layer 1).
//
// Single source of truth for "is this authenticated user allowed in during the
// private preview". FAIL-CLOSED by construction: an empty/unset allowlist
// matches NOBODY. A gate that silently lets everyone through when misconfigured
// is a fail-open bug (docs/OPERATING_RULES.md §1), so the empty case must deny.

// Parse the comma-separated ONELIVE_ALLOWLIST env value into a normalized list
// of lowercased, trimmed, non-empty emails.
export function parseAllowlist(raw: string | null | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter((entry) => entry.length > 0);
}

// Whether `email` is on `allowlist`. Case-insensitive. Returns false for a
// missing email OR an empty allowlist (fail-closed — never default to allow).
export function isAllowlisted(email: string | null | undefined, allowlist: string[]): boolean {
  if (allowlist.length === 0) return false;
  if (!email) return false;
  return allowlist.includes(email.trim().toLowerCase());
}

// Convenience: read + parse the allowlist from the environment at call time
// (so operators can rotate the allowlist without a rebuild).
export function allowlistFromEnv(raw: string | null | undefined = process.env.ONELIVE_ALLOWLIST): string[] {
  return parseAllowlist(raw);
}
