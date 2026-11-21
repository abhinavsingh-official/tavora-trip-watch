import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import type { NotificationReview } from '../types';

export default function OfferReview() {
  const { notificationId } = useParams();
  const navigate = useNavigate();
  const [review, setReview] = useState<NotificationReview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    if (!notificationId) return;
    api
      .reviewNotification(Number(notificationId))
      .then(setReview)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load offer'));
  }, [notificationId]);

  async function handleConfirm() {
    if (!review || review.current_observation.total_price === null) return;
    setBooking(true);
    setError(null);
    try {
      const result = await api.book(
        review.notification.request_id,
        review.notification.id,
        review.current_observation.total_price,
      );
      navigate(`/booking/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Booking failed');
    } finally {
      setBooking(false);
    }
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
    current_observation.status === 'complete' && current_observation.total_price !== null;

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

        {!canBook && (
          <p className="error-text">
            This package isn't currently complete ({current_observation.status}) - booking is
            disabled until a complete price is available.
          </p>
        )}

        <button onClick={handleConfirm} disabled={!canBook || booking}>
          {booking ? 'Booking...' : 'Confirm booking (simulated)'}
        </button>
      </div>
    </div>
  );
}
