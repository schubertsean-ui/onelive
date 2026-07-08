export type InboxItem = {
  candidate_id: string;
  title: string | null;
  start_time: string | null;
  venue_name: string | null;
  city: string | null;
  status: string;
  gate_reason: string | null;
  required_next: string | null;
};

export type Evidence = {
  evidence_id: string;
  source_class: string;
  source_name: string;
  source_url: string;
  quote: string;
  captured_at: string;
};

export type CandidateDetail = {
  candidate: any;
  evidence: Evidence[];
};
