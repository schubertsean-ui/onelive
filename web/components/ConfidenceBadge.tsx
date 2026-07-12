import { confidenceDisplay } from "../lib/confidence";

// A small, honest trust badge. The label and color both communicate state; the
// title + aria-label carry the full explanation for screen readers and hover.
export function ConfidenceBadge({ confidence }: { confidence: string | null | undefined }) {
  const d = confidenceDisplay(confidence);
  return (
    <span
      className="pub-badge"
      data-tone={d.tone}
      data-testid={`badge-confidence-${d.tone}`}
      title={d.blurb}
      aria-label={`Confidence: ${d.label}. ${d.blurb}`}
    >
      <span className="pub-badge-dot" aria-hidden="true" />
      {d.label}
    </span>
  );
}
