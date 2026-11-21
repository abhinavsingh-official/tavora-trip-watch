import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import type { NotificationReview } from '../types';

function useCountdown(heldUntil: string | null): number | null {
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  useEffect(() => {
    if (!heldUntil) {
      setSecondsLeft(null);
      return;
    }
    const target = new Date(heldUntil).getTime();
    const tick = () => setSecondsLeft(Math.max(0, Math.round((target - Date.now()) / 1000)));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [heldUntil]);

  return secondsLeft;
}

export default function OfferReview() {
  const { notificationId } = useParams();
  const navigate = useNavigate();
  const [review, setReview] = useState<NotificationReview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [holdExpired, setHoldExpired] = useState(false);
  const [booking, setBooking] = useState(false);
  const [reReviewing, setReReviewing] = useState(false);

  function loadReview() {
    if (!notificationId) return;
    setError(null);
    setHoldExpired(false);
    api
      .reviewNotification(Number(notificationId))
      .then(setReview)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load offer'));
  }

  useEffect(loadReview, [notificationId]);

  const secondsLeft = useCountdown(review?.notification.held_until ?? null);

  async function handleConfirm() {
    if (!review) return;
    setBooking(true);
    setError(null);
    try {
      const result = await api.book(review.notification.request_id, review.notification.id);
      navigate(`/booking/${result.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Booking failed';
      // The backend's hold-expiry rejection is a specific, expected outcome -
      // offer a fresh review instead of just a generic error.
      if (message.includes('expired')) {
        setHoldExpired(true);
      } else {
        setError(message);
      }
    } finally {
      setBooking(false);
    }
  }

  async function handleReReview() {
    setReReviewing(true);
    loadReview();
    setReReviewing(false);
  }

  if (error) {
    return (
      <div className="page">
        <p className="error-text">{error}</p>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="page">
        <p className="muted">Loading...</p>
      </div>
    );
  }

  const { original_observation, current_observation } = review;
  const priceChanged = original_observation.total_price !== current_observation.total_price;
  const canBook =
    current_observation.status === 'complete' &&
    current_observation.total_price !== null &&
    !holdExpired &&
    (secondsLeft === null || secondsLeft > 0);

  return (
    <div className="page">
      <h1>Review offer - Request #{review.notification.request_id}</h1>

      {priceChanged && (
        <p className="price-change-note">
          The price has changed since you were alerted: was ₹{original_observation.total_price},
          now ₹{current_observation.total_price}. This fresh total is what you'd be confirming,
          not the original alert.
        </p>
      )}

      {secondsLeft !== null && secondsLeft > 0 && (
        <p className="hold-countdown">Price held for {secondsLeft}s - book before it expires.</p>
      )}

      {(holdExpired || secondsLeft === 0) && (
        <p className="price-change-note">
          This hold has expired. Review again to get a fresh, bookable price.
        </p>
      )}

      <div className="card">
        <h2>Current itemized total</h2>
        <dl className="price-breakdown">
          <div>
            <dt>Flight</dt>
            <dd>
              ₹{current_observation.flight_outbound_price ?? '-'} + ₹
              {current_observation.flight_return_price ?? '-'}
            </dd>
          </div>
          <div>
            <dt>Hotel</dt>
            <dd>₹{current_observation.hotel_total_price ?? '-'}</dd>
          </div>
          <div>
            <dt>Cabs</dt>
            <dd>
              ₹{current_observation.cab_outbound_price ?? '-'} + ₹
              {current_observation.cab_return_price ?? '-'}
            </dd>
          </div>
          <div>
            <dt>Taxes/fees</dt>
            <dd>₹{current_observation.taxes_fees ?? '-'}</dd>
          </div>
          <div className="total-row">
            <dt>Total</dt>
            <dd>₹{current_observation.total_price ?? '-'}</dd>
          </div>
        </dl>

        {current_observation.status !== 'complete' && (
          <p className="error-text">
            This package isn't currently complete ({current_observation.status}) - booking is
            disabled until a complete price is available.
          </p>
        )}

        {holdExpired || secondsLeft === 0 ? (
          <button onClick={handleReReview} disabled={reReviewing}>
            {reReviewing ? 'Reviewing...' : 'Review again'}
          </button>
        ) : (
          <button onClick={handleConfirm} disabled={!canBook || booking}>
            {booking ? 'Booking...' : 'Confirm booking (simulated)'}
          </button>
        )}
      </div>
    </div>
  );
}
