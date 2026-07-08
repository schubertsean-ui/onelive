import { InboxItem } from "../lib/types";

export function CandidateTable({ items }: { items: InboxItem[] }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>When</th>
          <th>Title</th>
          <th>Venue</th>
          <th>Status</th>
          <th>Next</th>
        </tr>
      </thead>
      <tbody>
        {items.map((x) => (
          <tr key={x.candidate_id}>
            <td className="small">{x.start_time || "-"}</td>
            <td><a href={`/ops/candidate/${x.candidate_id}`}>{x.title || "(untitled)"}</a></td>
            <td>{x.venue_name || "-"}</td>
            <td>{x.status}</td>
            <td className="small">{x.required_next || x.gate_reason || ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
