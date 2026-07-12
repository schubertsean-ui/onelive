import { TonightEvent } from "../lib/public-types";
import { confidenceDisplay } from "../lib/confidence";
import { formatTime, formatDayLabel } from "../lib/time";
import { ConfidenceBadge } from "./ConfidenceBadge";

// A single event in the public feed. Renders EVERY event it is given, including
// disputed ones — trust state is shown, never used to hide the event.
export function EventCard({ event, now }: { event: TonightEvent; now?: Date }) {
  const d = confidenceDisplay(event.confidence);
  const venueName = event.venue?.name?.trim() || "Venue to be announced";
  const city = event.venue?.city?.trim();
  const time = formatTime(event.start_time);
  const day = formatDayLabel(event.start_time, now);

  return (
    <article
      className="pub-card"
      data-testid={`card-event-${event.event_id}`}
      aria-label={`${venueName}, ${day} ${time}, ${d.label}`}
    >
      <div className="pub-card-time">
        <span className="pub-time" data-testid="text-event-time">{time}</span>
        <span className="pub-time-day">{day}</span>
      </div>
      <div className="pub-card-body">
        <div className="pub-card-head">
          <div>
            <h3 className="pub-venue" data-testid="text-event-venue">{venueName}</h3>
            {city ? <p className="pub-venue-city">{city}</p> : null}
          </div>
          <ConfidenceBadge confidence={event.confidence} />
        </div>

        {event.notes?.trim() ? (
          <p className="pub-notes" data-testid="text-event-notes">{event.notes.trim()}</p>
        ) : null}

        {/* Cautioned states (disputed / unverified / unknown) always get an
            explicit inline explanation. Nothing is hidden or softened. */}
        {d.cautious ? (
          <div className="pub-caution" data-tone={d.tone} role="note" data-testid="note-caution">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 9v4m0 4h.01M10.3 3.3 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.3a2 2 0 0 0-3.4 0Z"
                stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>{d.blurb}</span>
          </div>
        ) : null}
      </div>
    </article>
  );
}
