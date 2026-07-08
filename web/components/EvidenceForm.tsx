"use client";
import { useState } from "react";
import { apiPost } from "../lib/api";

export function EvidenceForm({ candidateId, onDone }: { candidateId: string; onDone: () => void }) {
  const [source_class, setClass] = useState("ticketing");
  const [source_name, setName] = useState("");
  const [source_url, setUrl] = useState("");
  const [quote, setQuote] = useState("");

  async function submit() {
    await apiPost(`/ops/candidates/${candidateId}/evidence`, { source_class, source_name, source_url, quote });
    setName(""); setUrl(""); setQuote("");
    onDone();
  }

  return (
    <div className="card">
      <div className="h1">Add Evidence</div>
      <div className="row">
        <input className="input" value={source_class} onChange={(e) => setClass(e.target.value)} placeholder="source_class" />
        <input className="input" value={source_name} onChange={(e) => setName(e.target.value)} placeholder="source_name" />
      </div>
      <div style={{ marginTop: 8 }}>
        <input className="input" value={source_url} onChange={(e) => setUrl(e.target.value)} placeholder="source_url" />
      </div>
      <div style={{ marginTop: 8 }}>
        <textarea className="input" value={quote} onChange={(e) => setQuote(e.target.value)} placeholder="quote" rows={4} />
      </div>
      <div style={{ marginTop: 8 }}>
        <button className="btn btnPrimary" onClick={submit}>Add Evidence</button>
      </div>
    </div>
  );
}
