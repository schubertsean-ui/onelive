// Loading / empty / error presentations for the public feed. Each is a
// first-class, designed state — not an afterthought.

export function FeedSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="pub-feed" aria-hidden="true" data-testid="state-loading">
      {Array.from({ length: count }).map((_, i) => (
        <div className="pub-skel-card" key={i}>
          <div className="pub-card-time">
            <div className="pub-skel" style={{ height: 17, width: 52 }} />
            <div className="pub-skel" style={{ height: 11, width: 40, marginTop: 6 }} />
          </div>
          <div>
            <div className="pub-skel" style={{ height: 17, width: "58%" }} />
            <div className="pub-skel" style={{ height: 13, width: "34%", marginTop: 8 }} />
            <div className="pub-skel" style={{ height: 13, width: "82%", marginTop: 12 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function FeedEmpty({ city }: { city: string }) {
  return (
    <div className="pub-state" role="status" data-testid="state-empty">
      <svg className="pub-state-icon" width="34" height="34" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M8 2v3M16 2v3M3.5 9h17M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"
          stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <p className="pub-state-title">Nothing on the calendar yet</p>
      <p className="pub-state-body">
        We don&rsquo;t have any verified live events for {city} in this window right now.
        Check back soon &mdash; the feed updates as sources are confirmed.
      </p>
    </div>
  );
}

export function FeedError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="pub-state" role="alert" data-testid="state-error">
      <svg className="pub-state-icon" width="34" height="34" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 8v5m0 3h.01M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z"
          stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <p className="pub-state-title">We couldn&rsquo;t load tonight&rsquo;s events</p>
      <p className="pub-state-body">
        Something went wrong reaching the feed. Your connection may be down, or the
        service may be briefly unavailable.
      </p>
      <button className="pub-retry" onClick={onRetry} data-testid="button-retry">
        Try again
      </button>
    </div>
  );
}
