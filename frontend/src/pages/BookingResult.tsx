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

  useEffect(() => {
    if (!bookingId || currentUserId === null) return;
    api
      .getBooking(Number(bookingId), currentUserId)
      .then(setBooking)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load booking'));
  }, [bookingId, currentUserId]);

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
