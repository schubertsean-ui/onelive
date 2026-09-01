import { ClaimForm } from "../../../components/ClaimForm";

// Ops console reads the FastAPI backend (not part of the preview deploy) —
// render on demand, never prerender at build.
export const dynamic = "force-dynamic";

// The intake mailbox is served by the API (worker/claim/intake.py holds the one
// authority for it) so a changed address never needs a web redeploy. If the API
// is unreachable the form still works for the two modes that do not need it —
// the address is shown as unavailable rather than guessed.
async function forwardAddress(): Promise<string> {
  try {
    const { apiGet } = await import("../../../lib/ops-api");
    const options = await apiGet("/ops/claims/intake");
    return String(options.forward_to || "(intake address unavailable)");
  } catch {
    return "(intake address unavailable — API unreachable)";
  }
}

export default async function ClaimPage() {
  return <ClaimForm forwardTo={await forwardAddress()} />;
}
