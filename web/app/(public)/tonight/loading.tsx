import "./flow.css";

// Skeleton, not a spinner (nav canon §9.1): shape-matches the real feed —
// masthead, chip rows, card grid — so content lands with zero layout shift,
// and the CSS delays its own appearance ~200ms so fast loads never blink it.
// Purely presentational; aria-hidden with a polite busy note for AT.
export default function TonightLoading() {
  return (
    <main className="flow">
      <div className="wrap skel" aria-busy="true">
        <p className="visually-hidden" role="status">Loading tonight&rsquo;s events…</p>
        <div aria-hidden="true">
          <div className="sk sk-title" />
          <div className="sk sk-line" />
          <div className="sk-chiprow">
            <div className="sk sk-chip" /><div className="sk sk-chip" /><div className="sk sk-chip" />
          </div>
          <div className="sk-chiprow">
            <div className="sk sk-chip" /><div className="sk sk-chip" /><div className="sk sk-chip" /><div className="sk sk-chip" />
          </div>
          <div className="sk-grid">
            <div className="sk sk-card" /><div className="sk sk-card" /><div className="sk sk-card" />
          </div>
        </div>
      </div>
    </main>
  );
}
