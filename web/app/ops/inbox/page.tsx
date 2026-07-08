import { apiGet } from "../../../lib/api";
import { CandidateTable } from "../../../components/CandidateTable";

export default async function InboxPage() {
  const items = await apiGet("/ops/candidates/inbox?status=needs_review");
  return (
    <div className="card">
      <div className="h1">Ops Inbox</div>
      <CandidateTable items={items} />
    </div>
  );
}
