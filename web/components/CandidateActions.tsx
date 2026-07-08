"use client";
import { apiPost } from "../lib/api";
import { useState } from "react";

export function CandidateActions({ candidateId }: { candidateId: string }) {
  const [msg, setMsg] = useState<string>("");

  async function promote() {
    setMsg("");
    try {
      const r = await apiPost(`/ops/candidates/${candidateId}/promote`, {});
      setMsg(`Promoted -> event_id: ${r.event_id}`);
    } catch (e: any) {
      setMsg(e.message || "Error");
    }
  }

  return (
    <div className="card">
      <div className="h1">Actions</div>
      <button className="btn btnPrimary" onClick={promote}>Promote to Canonical Event</button>
      {msg ? <div className="small" style={{ marginTop: 8 }}>{msg}</div> : null}
    </div>
  );
}
