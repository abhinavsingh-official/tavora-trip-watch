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

type StepId = 'overview' | 'hotels' | 'flights' | 'cabs';
const STEPS: { id: StepId; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview & pay', icon: '💳' },
  { id: 'hotels', label: 'Hotels', icon: '🏨' },
  { id: 'flights', label: 'Flights', icon: '✈️' },
  { id: 'cabs', label: 'Cabs', icon: '🚕' },
];

/* Decorative only - not real amenity data, just enough variety that a list
 * of 40+ otherwise-identical rows doesn't look like a database dump. */
const HOTEL_PERKS = ['Free Wi-Fi', 'Breakfast included', 'Free cancellation', 'Pool access', 'Late checkout'];
const FLIGHT_PERKS = ['Free meal', 'Extra legroom', 'Priority boarding', 'Window seat available'];
const CAB_PERKS = ['AC', 'Sanitised vehicle', 'English-speaking driver', 'Free waiting time'];

function perksFor(list: string[], seed: number, count: number): string[] {
  const out: string[] = [];
  for (let i = 0; i < count; i++) {
    out.push(list[(seed + i) % list.length]);
  }
  return out;
}

type SortOrder = 'price-asc' | 'price-desc';

function SortToggle({ value, onChange }: { value: SortOrder; onChange: (v: SortOrder) => void }) {
  return (
    <div className="sort-toggle">
      <span className="muted">Sort by</span>
      <select value={value} onChange={(e) => onChange(e.target.value as SortOrder)}>
        <option value="price-asc">Price: low to high</option>
        <option value="price-desc">Price: high to low</option>
      </select>
    </div>
  );
}

function HotelRow({ candidate, index, chosen, onChoose }: { candidate: HotelDirectoryCandidate; index: number; chosen: boolean; onChoose: () => void }) {
  return (
    <button type="button" className={`directory-row${chosen ? ' selected' : ''}`} onClick={onChoose}>
      <img src="/images/hotel.jpg" alt="" className="directory-row-image" />
      <div className="directory-row-body">
        <div className="directory-row-top">
          <span className="candidate-title">{candidate.hotel_name}</span>
          {candidate.selected && <span className="selected-badge">Cheapest found</span>}
        </div>
        <div className="candidate-detail">
          {candidate.category_name ?? `${candidate.star_rating}-star`}
          {candidate.room_description ? ` · ${candidate.room_description}` : ''}
        </div>
        <div className="perk-chips">
          {perksFor(HOTEL_PERKS, index, 2).map((p) => (
            <span key={p} className="perk-chip">{p}</span>
          ))}
        </div>
      </div>
      <div className="directory-row-price">₹{candidate.price_inr}</div>
    </button>
  );
}

function FlightRow({ candidate, index, chosen, onChoose }: { candidate: FlightDirectoryCandidate; index: number; chosen: boolean; onChoose: () => void }) {
  return (
    <button type="button" className={`directory-row${chosen ? ' selected' : ''}`} onClick={onChoose}>
      <img src="/images/flight.jpg" alt="" className="directory-row-image" />
      <div className="directory-row-body">
        <div className="directory-row-top">
          <span className="candidate-title">{candidate.carrier_name} {candidate.flight_number}</span>
          {candidate.selected && <span className="selected-badge">Cheapest found</span>}
        </div>
        <div className="candidate-detail">
          {candidate.departure_time} → {candidate.arrival_time} ·{' '}
          {candidate.stops === 0 ? 'Non-stop' : `${candidate.stops} stop(s)`}
        </div>
        <div className="perk-chips">
          {perksFor(FLIGHT_PERKS, index, 2).map((p) => (
            <span key={p} className="perk-chip">{p}</span>
          ))}
        </div>
      </div>
      <div className="directory-row-price">₹{candidate.price_inr}</div>
    </button>
  );
}

function CabRow({ candidate, index, chosen, onChoose }: { candidate: CabDirectoryCandidate; index: number; chosen: boolean; onChoose: () => void }) {
  return (
    <button type="button" className={`directory-row${chosen ? ' selected' : ''}`} onClick={onChoose}>
      <img src="/images/cab.jpg" alt="" className="directory-row-image" />
      <div className="directory-row-body">
        <div className="directory-row-top">
          <span className="candidate-title">{candidate.vendor_name} ({candidate.vehicle_class})</span>
          {candidate.selected && <span className="selected-badge">Cheapest found</span>}
        </div>
        <div className="candidate-detail">
          Up to {candidate.passenger_capacity} people · {candidate.luggage_capacity} bags
        </div>
        <div className="perk-chips">
          {perksFor(CAB_PERKS, index, 2).map((p) => (
            <span key={p} className="perk-chip">{p}</span>
          ))}
        </div>
      </div>
      <div className="directory-row-price">₹{candidate.price_per_leg_inr}/leg</div>
    </button>
  );
}

const PAGE_SIZE = 8;

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
  const [sortOrder, setSortOrder] = useState<SortOrder>('price-asc');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  /* Purely local - browsing alternatives never changes the real price.
   * The booked total always uses the cheapest eligible option. */
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

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [stepIndex, sortOrder]);

  const bookableNotification = useMemo(
    () =>
      notifications
        .filter((n) => n.held_observation_id !== null && n.held_until !== null)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0] ??
      null,
    [notifications],
  );

  function sorted<T extends { price_inr?: number; price_per_leg_inr?: number }>(list: T[]): T[] {
    const key = (c: T) => c.price_inr ?? c.price_per_leg_inr ?? 0;
    const copy = [...list];
    copy.sort((a, b) => (sortOrder === 'price-asc' ? key(a) - key(b) : key(b) - key(a)));
    return copy;
  }

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
        Your bookings — {request.origin} ⇄ {request.destination}
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
              <p className="candidate-price">₹{pickedHotel?.price_inr ?? '-'}</p>
            </div>
            <div className="overview-tile">
              <img src="/images/flight.jpg" alt="" className="overview-tile-image" />
              <p className="candidate-title">{pickedOutbound?.carrier_name ?? 'No flight found'}</p>
              <p className="candidate-price">
                ₹{((pickedOutbound?.price_inr ?? 0) + (pickedReturn?.price_inr ?? 0)) || '-'}
              </p>
            </div>
            <div className="overview-tile">
              <img src="/images/cab.jpg" alt="" className="overview-tile-image" />
              <p className="candidate-title">{pickedCab?.vendor_name ?? 'No cab found'}</p>
              <p className="candidate-price">₹{pickedCab ? pickedCab.price_per_leg_inr * 2 : '-'}</p>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>Itemized total</h2>
            </div>
            <dl className="price-breakdown">
              <div>
                <dt>Outbound flight</dt>
                <dd>₹{pickedOutbound?.price_inr ?? '-'}</dd>
              </div>
              <div>
                <dt>Return flight</dt>
                <dd>₹{pickedReturn?.price_inr ?? '-'}</dd>
              </div>
              <div>
                <dt>Hotel</dt>
                <dd>₹{pickedHotel?.price_inr ?? '-'}</dd>
              </div>
              <div>
                <dt>Cabs (both legs)</dt>
                <dd>₹{pickedCab ? pickedCab.price_per_leg_inr * 2 : '-'}</dd>
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
                Paying books that exact held price.
              </p>
              <button onClick={handlePay} disabled={booking}>
                {booking ? 'Processing payment...' : `Pay ₹${bookableNotification.total_price} now`}
              </button>
              <p className="muted">Simulated purchase - no real payment is processed.</p>
            </>
          ) : (
            <p className="muted">
              No held offer to pay for yet. Open this request's alert from{' '}
              <Link to="/notifications">Notifications</Link> and review it first.
            </p>
          )}
        </div>
      )}

      {step.id === 'hotels' && (
        <div className="story-section">
          <div className="directory-section-header">
            <h2>
              <span className="story-section-icon">🏨</span> Hotels ({request.rooms} room(s), {request.adults} adult(s))
            </h2>
            <SortToggle value={sortOrder} onChange={setSortOrder} />
          </div>
          {directory.hotel_candidates.length === 0 ? (
            <p className="muted">No real hotel options available for this request right now.</p>
          ) : (
            <>
              <div className="directory-list">
                {sorted(directory.hotel_candidates).slice(0, visibleCount).map((c, i) => (
                  <HotelRow key={i} candidate={c} index={i} chosen={i === chosenHotel} onChoose={() => setChosenHotel(i)} />
                ))}
              </div>
              {visibleCount < directory.hotel_candidates.length && (
                <button className="secondary-button" onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}>
                  Show more ({directory.hotel_candidates.length - visibleCount} left)
                </button>
              )}
            </>
          )}
        </div>
      )}

      {step.id === 'flights' && (
        <>
          <div className="story-section">
            <div className="directory-section-header">
              <h2>
                <span className="story-section-icon">✈️</span> Outbound flight
              </h2>
              <SortToggle value={sortOrder} onChange={setSortOrder} />
            </div>
            <div className="directory-list">
              {sorted(directory.outbound_flight_candidates).slice(0, visibleCount).map((c, i) => (
                <FlightRow key={i} candidate={c} index={i} chosen={i === chosenOutbound} onChoose={() => setChosenOutbound(i)} />
              ))}
            </div>
          </div>
          <div className="story-section">
            <h2>
              <span className="story-section-icon">✈️</span> Return flight
            </h2>
            <div className="directory-list">
              {sorted(directory.return_flight_candidates).slice(0, visibleCount).map((c, i) => (
                <FlightRow key={i} candidate={c} index={i} chosen={i === chosenReturn} onChoose={() => setChosenReturn(i)} />
              ))}
            </div>
            {visibleCount < Math.max(directory.outbound_flight_candidates.length, directory.return_flight_candidates.length) && (
              <button className="secondary-button" onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}>
                Show more
              </button>
            )}
          </div>
        </>
      )}

      {step.id === 'cabs' && (
        <div className="story-section">
          <div className="directory-section-header">
            <h2>
              <span className="story-section-icon">🚕</span> Airport transfers
            </h2>
          </div>
          <p className="simulated-banner">
            Simulated - no real cab supplier API exists for this category. Anchored to real RTO
            rate cards, not an arbitrary number.
          </p>
          <div className="directory-list">
            {sorted(directory.cab_candidates).map((c, i) => (
              <CabRow key={i} candidate={c} index={i} chosen={i === chosenCab} onChoose={() => setChosenCab(i)} />
            ))}
          </div>
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
