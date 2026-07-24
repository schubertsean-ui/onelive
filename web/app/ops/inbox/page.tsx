import { apiGet } from "../../../lib/api";
import { CandidateTable } from "../../../components/CandidateTable";

// Ops console reads the FastAPI backend (not part of the preview deploy) —
// render on demand, never prerender at build.
export const dynamic = "force-dynamic";

export default async function InboxPage() {
  const items = await apiGet("/ops/candidates/inbox?status=needs_review");
  return (
    <div className="card">
      <div className="h1">Ops Inbox</div>
      <CandidateTable items={items} />
    </div>
  );
}
