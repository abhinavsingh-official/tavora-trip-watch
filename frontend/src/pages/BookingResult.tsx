import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
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
          <h2>Request #{booking.request_id}</h2>
          <span className={`status-tag status-${booking.aggregate_status}`}>
            {booking.aggregate_status}
          </span>
        </div>

        <p>Accepted total: ₹{booking.accepted_total}</p>

        {booking.aggregate_status === 'needs_reconciliation' && (
          <div className="price-change-note">
            <p>
              A supplier's response never resolved (simulated timeout) - the outcome is unknown
              until it's reconciled. No new booking attempt can be made until this is resolved.
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
            A compensating cancellation failed - the affected component below is still confirmed
            with its supplier and needs manual follow-up; this is not a completed rollback.
          </div>
        )}

        {booking.aggregate_status === 'in_progress' && (
          <div className="price-change-note">
            This booking stopped partway through (simulated restart). Revisiting this request's
            offer and booking again will resume it from where it left off, not start over.
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
