import { useEffect, useState } from 'react';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { BookingAttempt, TimelineEvent } from '../types';

export default function Ops() {
  const { currentUserId } = useCurrentUser();
  const [partialBookings, setPartialBookings] = useState<BookingAttempt[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (currentUserId === null) return;
    api
      .listPartialBookings(currentUserId)
      .then(setPartialBookings)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'));
  }, [currentUserId]);

  async function showTimeline(requestId: number) {
    if (currentUserId === null) return;
    setSelectedRequestId(requestId);
    try {
      const events = await api.getRequestTimeline(requestId, currentUserId);
      setTimeline(events);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timeline');
    }
  }

  return (
    <div className="page">
      <h1>Operations</h1>
      <p className="page-intro">
        Anything not fully confirmed - a partial booking needs a human to look at what
        actually happened and decide what to do about the pieces that didn't go through.
      </p>

      {error && <p className="error-text">{error}</p>}

      {partialBookings.length === 0 && (
        <p className="muted">Nothing stuck right now - every booking you've made is fully confirmed.</p>
      )}

      {partialBookings.map((b) => (
        <div key={b.id} className="card">
          <div className="card-header">
            <h2>Request #{b.request_id} - Booking #{b.id}</h2>
            <span className={`status-tag status-${b.aggregate_status}`}>{b.aggregate_status}</span>
          </div>
          <div className="booking-component-row">
            <span>Flight</span>
            <span className={`status-tag status-${b.flight_status}`}>{b.flight_status}</span>
          </div>
          <div className="booking-component-row">
            <span>Hotel</span>
            <span className={`status-tag status-${b.hotel_status}`}>{b.hotel_status}</span>
          </div>
          <div className="booking-component-row">
            <span>Cab</span>
            <span className={`status-tag status-${b.cab_status}`}>{b.cab_status}</span>
          </div>
          <button className="secondary-button" onClick={() => showTimeline(b.request_id)}>
            View event timeline
          </button>

          {selectedRequestId === b.request_id && (
            <ul className="timeline">
              {timeline.map((event, i) => (
                <li key={i} className={`timeline-event timeline-${event.type}`}>
                  <span className="muted">{new Date(event.at).toLocaleString()}</span> —{' '}
                  {event.summary}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
