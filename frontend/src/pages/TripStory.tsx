import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { FlightCandidate, HotelCandidate, TripRequest, TripStory as TripStoryData } from '../types';

function FlightCard({ candidate }: { candidate: FlightCandidate }) {
  return (
    <div className={`candidate-card${candidate.selected ? ' selected' : ''}`}>
      {candidate.selected && <span className="selected-badge">Picked</span>}
      <div className="candidate-title">
        {candidate.carrier_code} {candidate.flight_number}
      </div>
      <div className="candidate-detail">
        {candidate.departure_airport} {candidate.departure_time?.slice(0, 5)} →{' '}
        {candidate.arrival_airport} {candidate.arrival_time?.slice(0, 5)}
      </div>
      <div className="candidate-detail">
        {candidate.stops === 0 ? 'Non-stop' : `${candidate.stops} stop(s)`}
      </div>
      <div className="candidate-price">₹{candidate.price_inr}</div>
    </div>
  );
}

function HotelCard({ candidate }: { candidate: HotelCandidate }) {
  return (
    <div className={`candidate-card${candidate.selected ? ' selected' : ''}`}>
      {candidate.selected && <span className="selected-badge">Picked</span>}
      <div className="candidate-title">{candidate.name}</div>
      <div className="candidate-detail">{candidate.category_name ?? `${candidate.stars}-star`}</div>
      <div className="candidate-price">₹{candidate.price_inr}</div>
    </div>
  );
}

export default function TripStory() {
  const { requestId } = useParams();
  const { currentUserId } = useCurrentUser();
  const [request, setRequest] = useState<TripRequest | null>(null);
  const [story, setStory] = useState<TripStoryData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!requestId || currentUserId === null) return;
    setLoading(true);
    setError(null);
    Promise.all([
      api.getRequest(Number(requestId), currentUserId),
      api.getTripStory(Number(requestId), currentUserId),
    ])
      .then(([r, s]) => {
        setRequest(r);
        setStory(s);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load trip story'))
      .finally(() => setLoading(false));
  }, [requestId, currentUserId]);

  if (loading) {
    return (
      <div className="page">
        <p className="muted">Loading...</p>
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="page">
        <p className="error-text">{error ?? 'Request not found'}</p>
        <Link to="/dashboard" className="button-link secondary-button">
          Back to dashboard
        </Link>
      </div>
    );
  }

  if (!story) {
    return (
      <div className="page">
        <h1>
          {request.origin} ⇄ {request.destination}
        </h1>
        <p className="muted">No price checked yet - run "Check price now" from the dashboard first.</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>
        {request.origin} ⇄ {request.destination}
      </h1>
      <p className="page-intro">
        Every real flight and hotel option this request's last check actually found,
        from {new Date(story.observed_at).toLocaleString()} - not just the one price. The
        highlighted card is the cheapest eligible option, which is what the rest of the app
        uses as this trip's total.
      </p>

      <div className="story-section">
        <h2>
          <span className="story-section-icon">✈️</span> Outbound flight
        </h2>
        {story.outbound_flight_candidates.length === 0 ? (
          <p className="muted">No real flight options came back for this check.</p>
        ) : (
          <div className="candidate-row">
            {story.outbound_flight_candidates.map((c, i) => (
              <FlightCard key={i} candidate={c} />
            ))}
          </div>
        )}
      </div>

      <div className="story-section">
        <h2>
          <span className="story-section-icon">✈️</span> Return flight
        </h2>
        {story.return_flight_candidates.length === 0 ? (
          <p className="muted">No real flight options came back for this check.</p>
        ) : (
          <div className="candidate-row">
            {story.return_flight_candidates.map((c, i) => (
              <FlightCard key={i} candidate={c} />
            ))}
          </div>
        )}
      </div>

      <div className="story-section">
        <h2>
          <span className="story-section-icon">🏨</span> Hotel ({request.rooms} room(s),{' '}
          {request.adults} adult(s))
        </h2>
        {story.hotel_candidates.length === 0 ? (
          <p className="muted">
            No real hotel options met this request's filters on this check (min.{' '}
            {request.min_star_rating}-star).
          </p>
        ) : (
          <div className="candidate-row">
            {story.hotel_candidates.map((c, i) => (
              <HotelCard key={i} candidate={c} />
            ))}
          </div>
        )}
      </div>

      <div className="story-section">
        <h2>
          <span className="story-section-icon">🚕</span> Airport transfers
        </h2>
        <p className="simulated-banner">
          Simulated - no real cab supplier API exists for this category (see docs/DATA_SOURCE_DOSSIER.md).
          Anchored to real government per-km rate cards, not an arbitrary number.
        </p>
        <div className="candidate-row">
          <div className="candidate-card selected">
            <span className="selected-badge">Picked</span>
            <div className="candidate-title">Outbound transfer</div>
            <div className="candidate-price">₹{story.cab.outbound_price ?? '-'}</div>
          </div>
          <div className="candidate-card selected">
            <span className="selected-badge">Picked</span>
            <div className="candidate-title">Return transfer</div>
            <div className="candidate-price">₹{story.cab.return_price ?? '-'}</div>
          </div>
        </div>
      </div>

      <Link to="/dashboard" className="button-link secondary-button">
        ← Back to dashboard
      </Link>
    </div>
  );
}
