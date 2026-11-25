import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { formatInr } from '../format';
import { useCurrentUser } from '../UserContext';
import TripDirectoryBrowser from '../components/TripDirectoryBrowser';
import type { Notification, TripDirectory, TripRequest } from '../types';

type StepId = 'overview' | 'browse';
const STEPS: { id: StepId; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview & pay', icon: '💳' },
  { id: 'browse', label: 'Hotels, flights & cabs', icon: '🔍' },
];

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

  // A notification is for being told about a price change, not a required gate before buying
  async function handleBuyNow() {
    if (!requestId || currentUserId === null) return;
    setBooking(true);
    setError(null);
    try {
      const result = await api.buyNow(Number(requestId), currentUserId);
      navigate(`/booking/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Purchase failed');
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
  const pickedOutbound = directory.outbound_flight_candidates.find((c) => c.selected);
  const pickedReturn = directory.return_flight_candidates.find((c) => c.selected);
  const pickedHotel = directory.hotel_candidates.find((c) => c.selected);
  const pickedCab = directory.cab_candidates.find((c) => c.selected);
  const itemizedTotal =
    (pickedOutbound?.price_inr ?? 0) +
    (pickedReturn?.price_inr ?? 0) +
    (pickedHotel?.price_inr ?? 0) +
    (pickedCab?.price_per_leg_inr ?? 0) * 2;

  return (
    <div className="page your-bookings-page">
      <img src="/images/destination.jpg" alt="" className="your-bookings-hero" />
      <h1>
        Your bookings - {request.origin} ⇄ {request.destination}
      </h1>
      <p className="page-intro">
        Real hotel, flight, and cab options this request's monitoring found. Browsing is just for
        looking around - the booked price always uses the cheapest eligible option.
      </p>

      <div className="booking-steps">
        {STEPS.map((s, i) => (
          <button
            key={s.id}
            type="button"
            className={`booking-step${i === stepIndex ? ' active' : ''}`}
            onClick={() => setStepIndex(i)}
          >
            <span className="booking-step-icon">{s.icon}</span> {s.label}
          </button>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}

      {step.id === 'overview' && (
        <div className="story-section">
          <div className="overview-grid">
            <div className="overview-tile">
              <img src="/images/hotel.jpg" alt="" className="overview-tile-image" />
              <p className="candidate-title">{pickedHotel?.hotel_name ?? 'No hotel found'}</p>
              <p className="candidate-price">₹{formatInr(pickedHotel?.price_inr)}</p>
            </div>
            <div className="overview-tile">
              <img src="/images/flight.jpg" alt="" className="overview-tile-image" />
              <p className="candidate-title">{pickedOutbound?.carrier_name ?? 'No flight found'}</p>
              <p className="candidate-price">
                ₹{formatInr((pickedOutbound?.price_inr ?? 0) + (pickedReturn?.price_inr ?? 0) || undefined)}
              </p>
            </div>
            <div className="overview-tile">
              <img src="/images/cab.jpg" alt="" className="overview-tile-image" />
              <p className="candidate-title">{pickedCab?.vendor_name ?? 'No cab found'}</p>
              <p className="candidate-price">
                ₹{formatInr(pickedCab ? pickedCab.price_per_leg_inr * 2 : undefined)}
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>Itemized total</h2>
            </div>
            <dl className="price-breakdown">
              <div>
                <dt>Outbound flight</dt>
                <dd>₹{formatInr(pickedOutbound?.price_inr)}</dd>
              </div>
              <div>
                <dt>Return flight</dt>
                <dd>₹{formatInr(pickedReturn?.price_inr)}</dd>
              </div>
              <div>
                <dt>Hotel</dt>
                <dd>₹{formatInr(pickedHotel?.price_inr)}</dd>
              </div>
              <div>
                <dt>Cabs (both legs)</dt>
                <dd>₹{formatInr(pickedCab ? pickedCab.price_per_leg_inr * 2 : undefined)}</dd>
              </div>
              <div className="total-row">
                <dt>Approximate total</dt>
                <dd>₹{formatInr(itemizedTotal)}</dd>
              </div>
            </dl>
          </div>

          {bookableNotification && (
            <>
              <p className="muted">
                A reviewed, held offer is available at ₹{formatInr(bookableNotification.total_price)} until{' '}
                {bookableNotification.held_until ? new Date(bookableNotification.held_until).toLocaleTimeString() : 'now'}.
                Paying books that exact held price.
              </p>
              <button onClick={handlePay} disabled={booking}>
                {booking ? 'Processing payment...' : `Pay ₹${formatInr(bookableNotification.total_price)} now`}
              </button>
            </>
          )}
          <p className="muted">
            Don't want to wait for an alert? Buy at today's price directly - this checks the price
            right now and books it in the same click.
          </p>
          <button className="secondary-button" onClick={handleBuyNow} disabled={booking}>
            {booking ? 'Processing...' : 'Buy now at today\'s price'}
          </button>
          <p className="muted">Simulated purchase - no real payment is processed.</p>
        </div>
      )}

      {step.id === 'browse' && <TripDirectoryBrowser directory={directory} />}

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
