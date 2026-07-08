import { apiGet } from "../../../../lib/api";
import { EvidenceForm } from "../../../../components/EvidenceForm";
import { CandidateActions } from "../../../../components/CandidateActions";

export default async function CandidatePage({ params }: { params: { id: string } }) {
  const data = await apiGet(`/ops/candidates/${params.id}`);
  const c = data.candidate;
  return (
    <div className="row">
      <div style={{ flex: 2, minWidth: 320 }}>
        <div className="card">
          <div className="h1">{c.title || "Candidate"}</div>
          <div className="small">candidate_id: {c.candidate_id}</div>
          <div style={{ marginTop: 8 }}><b>When:</b> {c.start_time || "-"}</div>
          <div><b>Venue:</b> {c.venue_name || "-"}</div>
          <div><b>Artists:</b> {(c.artist_names || []).join(", ")}</div>
          <div style={{ marginTop: 8 }}><b>Status:</b> {c.status}</div>
          <div className="small" style={{ marginTop: 8 }}><b>Raw:</b><br />{(c.raw_text || "").slice(0, 800)}</div>
        </div>
        <div style={{ marginTop: 12 }}>
          <EvidenceForm candidateId={params.id} onDone={() => { /* refresh via reload */ }} />
        </div>
      </div>
      <div style={{ flex: 1, minWidth: 280 }}>
        <CandidateActions candidateId={params.id} />
        <div style={{ marginTop: 12 }} className="card">
          <div className="h1">Evidence</div>
          {(data.evidence || []).map((e: any) => (
            <div key={e.evidence_id} style={{ marginBottom: 10 }}>
              <div><b>{e.source_class}</b> — {e.source_name}</div>
              <div className="small">{e.source_url}</div>
              <div className="small">{(e.quote || "").slice(0, 180)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
