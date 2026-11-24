import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type {
  CabDirectoryCandidate,
  FlightDirectoryCandidate,
  HotelDirectoryCandidate,
  Notification,
  TripDirectory,
  TripRequest,
} from '../types';

type StepId = 'hotels' | 'flights' | 'cabs' | 'summary';
const STEPS: { id: StepId; label: string; icon: string }[] = [
  { id: 'hotels', label: 'Hotels', icon: '🏨' },
  { id: 'flights', label: 'Flights', icon: '✈️' },
  { id: 'cabs', label: 'Cabs', icon: '🚕' },
  { id: 'summary', label: 'Review & pay', icon: '💳' },
];

function FlightCard({
  candidate,
  chosen,
  onChoose,
}: {
  candidate: FlightDirectoryCandidate;
  chosen: boolean;
  onChoose: () => void;
}) {
  return (
    <button
      type="button"
      className={`candidate-card directory-card${chosen ? ' selected' : ''}`}
      onClick={onChoose}
    >
      {candidate.selected && <span className="selected-badge">Cheapest found</span>}
      <img src="/images/flight.jpg" alt="" className="directory-card-image" />
      <div className="candidate-title">
        {candidate.carrier_name} {candidate.flight_number}
      </div>
      <div className="candidate-detail">
        {candidate.departure_time} → {candidate.arrival_time}
      </div>
      <div className="candidate-detail">
        {candidate.stops === 0 ? 'Non-stop' : `${candidate.stops} stop(s)`}
      </div>
      <div className="candidate-price">₹{candidate.price_inr}</div>
    </button>
  );
}

function HotelCard({
  candidate,
  chosen,
  onChoose,
}: {
  candidate: HotelDirectoryCandidate;
  chosen: boolean;
  onChoose: () => void;
}) {
  return (
    <button
      type="button"
      className={`candidate-card directory-card${chosen ? ' selected' : ''}`}
      onClick={onChoose}
    >
      {candidate.selected && <span className="selected-badge">Cheapest found</span>}
      <img src="/images/hotel.jpg" alt="" className="directory-card-image" />
      <div className="candidate-title">{candidate.hotel_name}</div>
      <div className="candidate-detail">
        {candidate.category_name ?? `${candidate.star_rating}-star`}
        {candidate.room_description ? ` · ${candidate.room_description}` : ''}
      </div>
      <div className="candidate-price">₹{candidate.price_inr}</div>
    </button>
  );
}

function CabCard({
  candidate,
  chosen,
  onChoose,
}: {
  candidate: CabDirectoryCandidate;
  chosen: boolean;
  onChoose: () => void;
}) {
  return (
    <button
      type="button"
      className={`candidate-card directory-card${chosen ? ' selected' : ''}`}
      onClick={onChoose}
    >
      {candidate.selected && <span className="selected-badge">Cheapest found</span>}
      <img src="/images/cab.jpg" alt="" className="directory-card-image" />
      <div className="candidate-title">
        {candidate.vendor_name} ({candidate.vehicle_class})
      </div>
      <div className="candidate-detail">
        Up to {candidate.passenger_capacity} people · {candidate.luggage_capacity} bags
      </div>
      <div className="candidate-price">₹{candidate.price_per_leg_inr}/leg</div>
    </button>
  );
}

export default function YourBookings() {
  const { requestId } = useParams();
  const { currentUserId } = useCurrentUser();
  const navigate = useNavigate();

  const [request, setRequest] = useState<TripRequest | null>(null);
  const [directory, setDirectory] = useState<TripDirectory | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [stepIndex, setStepIndex] = useState(0);
  const [booking, setBooking] = useState(false);

  /* Purely local - browsing alternatives never changes the real price.
   * The booked total always uses the cheapest eligible option, same as
   * pricing.py; these just track which card is visually highlighted. */
  const [chosenHotel, setChosenHotel] = useState(0);
  const [chosenOutbound, setChosenOutbound] = useState(0);
  const [chosenReturn, setChosenReturn] = useState(0);
  const [chosenCab, setChosenCab] = useState(0);

  useEffect(() => {
    if (!requestId || currentUserId === null) return;
    setLoading(true);
    setError(null);
    Promise.all([
      api.getRequest(Number(requestId), currentUserId),
      api.getTripDirectory(Number(requestId), currentUserId),
      api.listNotifications(currentUserId),
    ])
      .then(([r, d, allNotifications]) => {
        setRequest(r);
        setDirectory(d);
        setNotifications(allNotifications.filter((n) => n.request_id === Number(requestId)));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load this trip'))
      .finally(() => setLoading(false));
  }, [requestId, currentUserId]);

  const bookableNotification = useMemo(
    () =>
      notifications
        .filter((n) => n.held_observation_id !== null && n.held_until !== null)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0] ??
      null,
    [notifications],
  );

  async function handlePay() {
    if (!requestId || currentUserId === null || !bookableNotification) return;
    setBooking(true);
    setError(null);
    try {
      const result = await api.book(Number(requestId), bookableNotification.id, currentUserId);
      navigate(`/booking/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Payment failed');
    } finally {
      setBooking(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p className="muted">Loading...</p>
      </div>
    );
  }

  if (error && !request) {
    return (
      <div className="page">
        <p className="error-text">{error}</p>
        <Link to="/dashboard" className="button-link secondary-button">
          Back to dashboard
        </Link>
      </div>
    );
  }

  if (!request || !directory) {
    return null;
  }

  const step = STEPS[stepIndex];
  const itemizedTotal =
    (directory.outbound_flight_candidates.find((c) => c.selected)?.price_inr ?? 0) +
    (directory.return_flight_candidates.find((c) => c.selected)?.price_inr ?? 0) +
    (directory.hotel_candidates.find((c) => c.selected)?.price_inr ?? 0) +
    (directory.cab_candidates.find((c) => c.selected)?.price_per_leg_inr ?? 0) * 2;

  return (
    <div className="page your-bookings-page">
      <img src="/images/destination.jpg" alt="" className="your-bookings-hero" />
      <h1>
        Your bookings — {request.origin} ⇄ {request.destination}
      </h1>
      <p className="page-intro">
        Browse the real alternatives this request's monitoring actually found, then review and
        pay. Switching the highlighted card below is just for looking around - the price that
        gets booked always uses the cheapest eligible option, exactly like the rest of the app.
      </p>

      <div className="booking-steps">
        {STEPS.map((s, i) => (
          <button
            key={s.id}
            type="button"
            className={`booking-step${i === stepIndex ? ' active' : ''}${i < stepIndex ? ' done' : ''}`}
            onClick={() => setStepIndex(i)}
          >
            <span className="booking-step-icon">{s.icon}</span> {s.label}
          </button>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}

      {step.id === 'hotels' && (
        <div className="story-section">
          <h2>
            <span className="story-section-icon">🏨</span> Hotels ({request.rooms} room(s),{' '}
            {request.adults} adult(s))
          </h2>
          {directory.hotel_candidates.length === 0 ? (
            <p className="muted">No real hotel options available for this request right now.</p>
          ) : (
            <div className="candidate-row">
              {directory.hotel_candidates.map((c, i) => (
                <HotelCard key={i} candidate={c} chosen={i === chosenHotel} onChoose={() => setChosenHotel(i)} />
              ))}
            </div>
          )}
        </div>
      )}

      {step.id === 'flights' && (
        <>
          <div className="story-section">
            <h2>
              <span className="story-section-icon">✈️</span> Outbound flight
            </h2>
            <div className="candidate-row">
              {directory.outbound_flight_candidates.map((c, i) => (
                <FlightCard key={i} candidate={c} chosen={i === chosenOutbound} onChoose={() => setChosenOutbound(i)} />
              ))}
            </div>
          </div>
          <div className="story-section">
            <h2>
              <span className="story-section-icon">✈️</span> Return flight
            </h2>
            <div className="candidate-row">
              {directory.return_flight_candidates.map((c, i) => (
                <FlightCard key={i} candidate={c} chosen={i === chosenReturn} onChoose={() => setChosenReturn(i)} />
              ))}
            </div>
          </div>
        </>
      )}

      {step.id === 'cabs' && (
        <div className="story-section">
          <h2>
            <span className="story-section-icon">🚕</span> Airport transfers
          </h2>
          <p className="simulated-banner">
            Simulated - no real cab supplier API exists for this category. Anchored to real
            government per-km rate cards, not an arbitrary number.
          </p>
          <div className="candidate-row">
            {directory.cab_candidates.map((c, i) => (
              <CabCard key={i} candidate={c} chosen={i === chosenCab} onChoose={() => setChosenCab(i)} />
            ))}
          </div>
        </div>
      )}

      {step.id === 'summary' && (
        <div className="story-section">
          <h2>Review &amp; pay</h2>
          <div className="card">
            <div className="card-header">
              <h2>Itemized total (cheapest eligible option of each)</h2>
            </div>
            <dl className="price-breakdown">
              <div>
                <dt>Outbound flight</dt>
                <dd>₹{directory.outbound_flight_candidates.find((c) => c.selected)?.price_inr ?? '-'}</dd>
              </div>
              <div>
                <dt>Return flight</dt>
                <dd>₹{directory.return_flight_candidates.find((c) => c.selected)?.price_inr ?? '-'}</dd>
              </div>
              <div>
                <dt>Hotel</dt>
                <dd>₹{directory.hotel_candidates.find((c) => c.selected)?.price_inr ?? '-'}</dd>
              </div>
              <div>
                <dt>Cabs (both legs)</dt>
                <dd>
                  ₹
                  {directory.cab_candidates.find((c) => c.selected)
                    ? directory.cab_candidates.find((c) => c.selected)!.price_per_leg_inr * 2
                    : '-'}
                </dd>
              </div>
              <div className="total-row">
                <dt>Approximate total</dt>
                <dd>₹{Math.round(itemizedTotal)}</dd>
              </div>
            </dl>
          </div>

          {bookableNotification ? (
            <>
              <p className="muted">
                A reviewed, held offer is available at ₹{bookableNotification.total_price} until{' '}
                {bookableNotification.held_until ? new Date(bookableNotification.held_until).toLocaleTimeString() : 'now'}.
                Paying books that exact held price, not whatever is shown above.
              </p>
              <button onClick={handlePay} disabled={booking}>
                {booking ? 'Processing payment...' : `Pay ₹${bookableNotification.total_price} now`}
              </button>
              <p className="muted">Simulated purchase - no real payment is processed.</p>
            </>
          ) : (
            <p className="muted">
              No actively held offer to pay for yet. Open this request's alert from{' '}
              <Link to="/notifications">Notifications</Link> and review it first - that's what
              locks in a price you can actually pay.
            </p>
          )}
        </div>
      )}

      <div className="card-actions booking-step-nav">
        <button
          className="secondary-button"
          disabled={stepIndex === 0}
          onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
        >
          ← Previous
        </button>
        <button
          className="secondary-button"
          disabled={stepIndex === STEPS.length - 1}
          onClick={() => setStepIndex((i) => Math.min(STEPS.length - 1, i + 1))}
        >
          Next →
        </button>
        <Link to="/dashboard" className="button-link secondary-button">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
