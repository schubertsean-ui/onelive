import { ClaimForm } from "../../../components/ClaimForm";

// Ops console reads the FastAPI backend (not part of the preview deploy) —
// render on demand, never prerender at build.
export const dynamic = "force-dynamic";

// The intake mailbox is served by the API (worker/claim/intake.py holds the one
// authority) so a changed address never needs a web redeploy. It legitimately
// comes back EMPTY when no mailbox is configured — that is a real state, and the
// form renders the email route as closed rather than inventing an address. An
// unreachable API is the same story: return "" and let the form say so.
async function forwardAddress(): Promise<string> {
  try {
    const { apiGet } = await import("../../../lib/ops-api");
    const options = await apiGet("/ops/claims/intake");
    return String(options.forward_to || "");
  } catch {
    return "";
  }
}

export default async function ClaimPage() {
  return <ClaimForm forwardTo={await forwardAddress()} />;
}
