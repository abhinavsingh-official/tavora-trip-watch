import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import { formatInr } from '../format';
import { useCurrentUser } from '../UserContext';
import type { BookingAttempt } from '../types';

function ComponentRow({
  label,
  status,
  supplierRef,
}: {
  label: string;
  status: string;
  supplierRef: string | null;
}) {
  return (
    <div className="booking-component-row">
      <span>{label}</span>
      <span className={`status-tag status-${status}`}>{status}</span>
      <code>{supplierRef ?? '-'}</code>
    </div>
  );
}

export default function BookingResult() {
  const { bookingId } = useParams();
  const { currentUserId } = useCurrentUser();
  const [booking, setBooking] = useState<BookingAttempt | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!bookingId || currentUserId === null) return;
    api
      .getBooking(Number(bookingId), currentUserId)
      .then(setBooking)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load booking'));
  }

  useEffect(load, [bookingId, currentUserId]);

  async function handleReconcile(outcome: 'confirmed' | 'failed') {
    if (!bookingId || currentUserId === null) return;
    const updated = await api.reconcileBooking(Number(bookingId), currentUserId, outcome);
    setBooking(updated);
  }

  if (error) {
    return (
      <div className="page">
        <p className="error-text">{error}</p>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="page">
        <p className="muted">Loading...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Booking result</h1>
      <p className="simulated-banner">
        This is a simulated booking - no real purchase or payment occurred.
      </p>

      <div className="card">
        <div className="card-header">
          <h2>Request #{booking.request_id} · Booking #{booking.id}</h2>
          <span className={`status-tag status-${booking.aggregate_status}`}>
            {booking.aggregate_status}
          </span>
        </div>

        <dl className="price-breakdown">
          <div className="total-row">
            <dt>Accepted total</dt>
            <dd>₹{formatInr(booking.accepted_total)}</dd>
          </div>
        </dl>

        {booking.aggregate_status === 'needs_reconciliation' && (
          <div className="price-change-note">
            <p>
              A supplier never responded (simulated timeout), so we don't know if this actually
              booked. Resolve it below before trying again.
            </p>
            <div className="card-actions">
              <button onClick={() => handleReconcile('confirmed')}>
                Reconcile: it was actually booked
              </button>
              <button className="secondary-button" onClick={() => handleReconcile('failed')}>
                Reconcile: it was never booked
              </button>
            </div>
          </div>
        )}

        {booking.aggregate_status === 'manual_intervention' && (
          <div className="price-change-note">
            A cancellation failed, so the component below is still booked with its supplier and
            needs manual follow-up.
          </div>
        )}

        {booking.aggregate_status === 'in_progress' && (
          <div className="price-change-note">
            This booking stopped partway through (simulated restart). Booking again will pick up
            where it left off.
          </div>
        )}

        <ComponentRow
          label="Flight"
          status={booking.flight_status}
          supplierRef={booking.supplier_ref_flight}
        />
        <ComponentRow
          label="Hotel"
          status={booking.hotel_status}
          supplierRef={booking.supplier_ref_hotel}
        />
        <ComponentRow label="Cab" status={booking.cab_status} supplierRef={booking.supplier_ref_cab} />
      </div>
    </div>
  );
}
