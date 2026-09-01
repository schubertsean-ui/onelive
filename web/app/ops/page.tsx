// Ops console — render on demand (never prerender), consistent with the rest of
// /ops so no ops route can regress into build-time coupling.
export const dynamic = "force-dynamic";

export default function OpsRoot() {
  return (
    <div className="card">
      <div className="h1">Ops</div>
      <div className="row">
        <a className="btn btnPrimary" href="/ops/inbox">Go to Inbox</a>
        <a className="btn" href="/ops/claim">Record a venue claim</a>
      </div>
    </div>
  );
}
