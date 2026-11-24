import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { formatInr } from '../format';
import { useCurrentUser } from '../UserContext';
import PriceHistoryChart from '../components/PriceHistoryChart';
import type { BookingAttempt, PriceObservation, TimelineEvent, TripRequest } from '../types';

function NeedsAttention({ currentUserId }: { currentUserId: number | null }) {
  const [partialBookings, setPartialBookings] = useState<BookingAttempt[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);

  useEffect(() => {
    if (currentUserId === null) return;
    api
      .listPartialBookings(currentUserId)
      .then(setPartialBookings)
      .catch(() => setPartialBookings([]));
  }, [currentUserId]);

  async function showTimeline(requestId: number) {
    if (currentUserId === null) return;
    setSelectedRequestId(requestId);
    try {
      setTimeline(await api.getRequestTimeline(requestId, currentUserId));
    } catch {
      setTimeline([]);
    }
  }

  if (partialBookings.length === 0) return null;

  return (
    <div className="card needs-attention-card">
      <div className="card-header">
        <h2>Needs attention</h2>
        <span className="muted">Bookings that didn't fully go through</span>
      </div>
      {partialBookings.map((b) => (
        <div key={b.id} className="needs-attention-row">
          <div className="card-header">
            <h3>Request #{b.request_id} · Booking #{b.id}</h3>
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
          <div className="card-actions">
            <Link to={`/booking/${b.id}`} className="button-link secondary-button">
              Resolve
            </Link>
            <button className="secondary-button" onClick={() => showTimeline(b.request_id)}>
              View event timeline
            </button>
          </div>
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

function StatusBadge({ status }: { status: string }) {
  /* active is the normal state, nothing to show for it */
  if (status === 'active') return null;
  return <span className={`status-tag status-${status}`}>{status}</span>;
}

/* Static, illustrative suggestions - not a real recommendation engine,
 * just a small fixed list so the dashboard feels like a live product
 * instead of only ever showing what you already asked for. */
const SUGGESTED_TRIPS = [
  { origin: 'Mumbai', destination: 'Udaipur', note: 'Lake palaces, 2-3 nights' },
  { origin: 'Delhi', destination: 'Manali', note: 'Hill-station escape' },
  { origin: 'Bengaluru', destination: 'Gokarna', note: 'Quiet beach alternative to Goa' },
  { origin: 'Mumbai', destination: 'Kochi', note: 'Backwaters and old-town streets' },
];

function RecommendedTrips({ existingDestinations }: { existingDestinations: string[] }) {
  const suggestions = SUGGESTED_TRIPS.filter(
    (s) => !existingDestinations.includes(s.destination),
  ).slice(0, 3);

  if (suggestions.length === 0) return null;

  return (
    <div className="card recommended-trips-card">
      <div className="card-header">
        <h2>Maybe your next trip?</h2>
      </div>
      <p className="muted">A few other places worth watching, just for fun.</p>
      <div className="candidate-row">
        {suggestions.map((s) => (
          <div key={s.destination} className="candidate-card">
            <img src="/images/destination.jpg" alt="" className="directory-card-image" />
            <div className="candidate-title">
              {s.origin} ⇄ {s.destination}
            </div>
            <div className="candidate-detail">{s.note}</div>
            <Link to="/new" className="button-link secondary-button">
              Start a watch
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}


/* Rough, human-readable "how long ago" - exact precision doesn't matter
   here, only whether it's recent enough to still trust at a glance. */
function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(ms / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} minute(s) ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour(s) ago`;
  const days = Math.round(hours / 24);
  return `${days} day(s) ago`;
}

/* Flights/hotels/cabs drift in the background on their own (see
   price_mutation.py) even with no edit to this request at all - a
   total that's stale purely from TIME passing, not from an edit, was
   previously invisible here and could look flatly wrong next to a
   freshly-checked buy price. 15 minutes is a few scheduler cycles. */
const STALE_AFTER_MINUTES = 15;

function ObservationSummary({
  observations,
  requestUpdatedAt,
  budget,
}: {
  observations: PriceObservation[];
  requestUpdatedAt: string;
  budget: number;
}) {
  const latest = observations[0] ?? null;
  if (!latest) {
    return <p className="muted">No price checked yet.</p>;
  }

  const latestValid = observations.find((o) => o.status === 'complete') ?? null;
  const validTotals = observations
    .filter((o) => o.status === 'complete' && o.total_price !== null)
    .map((o) => o.total_price as number);
  const lowestValid = validTotals.length > 0 ? Math.min(...validTotals) : null;

  /* edits don't touch past observations, so flag a total that predates the last edit */
  const isStaleFromEdit = new Date(latest.observed_at) < new Date(requestUpdatedAt);
  const minutesSinceChecked = Math.round((Date.now() - new Date(latest.observed_at).getTime()) / 60000);
  const isStaleFromAge = minutesSinceChecked >= STALE_AFTER_MINUTES;

  return (
    <>
      {isStaleFromEdit ? (
        <p className="price-change-note">
          This was checked before your last edit. Hit "Check price now" for a current total.
        </p>
      ) : (
        isStaleFromAge && (
          <p className="price-change-note">
            Checked {timeAgo(latest.observed_at)} - the market moves in the background, so this
            total may no longer match what you'd actually pay. Hit "Check price now" first.
          </p>
        )
      )}
      <dl className="price-breakdown">
      <div>
        <dt>Flight</dt>
        <dd>
          ₹{formatInr(latest.flight_outbound_price)} + ₹{formatInr(latest.flight_return_price)}
          {latest.flight_status !== 'complete' && (
            <span className="status-tag">{latest.flight_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Hotel</dt>
        <dd>
          ₹{formatInr(latest.hotel_total_price)}
          {latest.hotel_status !== 'complete' && (
            <span className="status-tag">{latest.hotel_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Cabs</dt>
        <dd>
          ₹{formatInr(latest.cab_outbound_price)} + ₹{formatInr(latest.cab_return_price)}
          {latest.cab_status !== 'complete' && (
            <span className="status-tag">{latest.cab_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Taxes/fees</dt>
        <dd>₹{formatInr(latest.taxes_fees)}</dd>
      </div>
      <div className="total-row">
        <dt>Latest check ({timeAgo(latest.observed_at)})</dt>
        <dd>
          ₹{formatInr(latest.total_price)}
          <span className={`status-tag status-${latest.status}`}>{latest.status}</span>
        </dd>
      </div>
      {latestValid && latestValid.id !== latest.id && (
        <div>
          <dt>Latest valid total</dt>
          <dd>₹{formatInr(latestValid.total_price)}</dd>
        </div>
      )}
      {lowestValid !== null && (
        <div>
          <dt>Lowest observed (valid)</dt>
          <dd>₹{formatInr(lowestValid)}</dd>
        </div>
      )}
      </dl>
      <PriceHistoryChart observations={observations} budget={budget} />
    </>
  );
}

export default function Dashboard() {
  const { currentUserId } = useCurrentUser();
  const [requests, setRequests] = useState<TripRequest[]>([]);
  const [history, setHistory] = useState<Record<number, PriceObservation[]>>({});
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  /* which card is mid-confirmation for cancel, since cancel is permanent */
  const [confirmingCancelId, setConfirmingCancelId] = useState<number | null>(null);

  async function loadHistory(requestId: number) {
    if (currentUserId === null) return;
    try {
      const observations = await api.listObservations(requestId, currentUserId);
      setHistory((prev) => ({ ...prev, [requestId]: observations }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load price history');
    }
  }

  useEffect(() => {
    if (currentUserId === null) return;
    api
      .listRequests(currentUserId)
      .then((fetched) => {
        setRequests(fetched);
        fetched.forEach((r) => loadHistory(r.id));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load requests'));
    /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [currentUserId]);

  async function handleCheck(requestId: number) {
    if (currentUserId === null) return;
    setCheckingId(requestId);
    setError(null);
    try {
      await api.checkPrice(requestId, currentUserId);
      await loadHistory(requestId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Check failed');
    } finally {
      setCheckingId(null);
    }
  }

  async function handleStatusChange(
    requestId: number,
    action: 'pause' | 'cancel' | 'reactivate',
  ) {
    if (currentUserId === null) return;
    setError(null);
    try {
      const updater =
        action === 'pause'
          ? api.pauseRequest
          : action === 'cancel'
            ? api.cancelRequest
            : api.reactivateRequest;
      const updated = await updater(requestId, currentUserId);
      setRequests((prev) => prev.map((r) => (r.id === requestId ? updated : r)));
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} request`);
    } finally {
      setConfirmingCancelId(null);
    }
  }

  async function handleResetToDefault(requestId: number) {
    if (currentUserId === null) return;
    setError(null);
    try {
      const updated = await api.resetRequestToDefault(requestId, currentUserId);
      setRequests((prev) => prev.map((r) => (r.id === requestId ? updated : r)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset this request');
    }
  }

  const activeAndPausedRequests = requests.filter((r) => r.status !== 'cancelled');

  return (
    <div className="page">
      <div className="page-header-row">
        <h1>Your requests</h1>
        <Link to="/new" className="button-link">
          + New request
        </Link>
      </div>
      <p className="page-intro">
        We check these every 5 minutes, or right now if you hit the button below.
      </p>

      {error && <p className="error-text">{error}</p>}

      <NeedsAttention currentUserId={currentUserId} />

      {activeAndPausedRequests.length === 0 && <p className="muted">No requests yet.</p>}

      {activeAndPausedRequests.map((r) => (
        <div key={r.id} className="card">
          <div className="card-header">
            <h2>
              {r.origin} ⇄ {r.destination} <StatusBadge status={r.status} />
            </h2>
            <span className="muted">
              {r.outbound_date} → {r.return_date} · {r.adults} adults · {r.rooms} room(s) ·
              budget ₹{formatInr(r.budget_inr)}
            </span>
          </div>

          <ObservationSummary
            observations={history[r.id] ?? []}
            requestUpdatedAt={r.updated_at}
            budget={r.budget_inr}
          />

          <div className="card-actions">
            <button onClick={() => handleCheck(r.id)} disabled={checkingId === r.id || r.status !== 'active'}>
              {checkingId === r.id ? 'Checking...' : 'Check price now'}
            </button>
            {/* no point editing a cancelled request, it can't come back */}
            {r.status !== 'cancelled' && (
              <Link to={`/requests/${r.id}/edit`} className="button-link secondary-button">
                Edit
              </Link>
            )}
            <Link to={`/requests/${r.id}/story`} className="button-link secondary-button">
              Your bookings
            </Link>
            {r.status === 'active' && (
              <button className="secondary-button" onClick={() => handleStatusChange(r.id, 'pause')}>
                Pause
              </button>
            )}
            {r.status === 'paused' && (
              <button
                className="secondary-button"
                onClick={() => handleStatusChange(r.id, 'reactivate')}
              >
                Resume
              </button>
            )}
            {r.status !== 'cancelled' && confirmingCancelId !== r.id && (
              <button className="secondary-button" onClick={() => setConfirmingCancelId(r.id)}>
                Cancel
              </button>
            )}
            {r.has_drifted_from_default && (
              <button
                className="secondary-button reset-default-button"
                onClick={() => handleResetToDefault(r.id)}
                title="Restore this request's original demo values"
              >
                Return to default
              </button>
            )}
          </div>

          {confirmingCancelId === r.id && (
            <div className="price-change-note">
              <p>Cancel this request? It'll move to Trash - you can restore it from there.</p>
              <div className="card-actions">
                <button onClick={() => handleStatusChange(r.id, 'cancel')}>Yes, cancel it</button>
                <button className="secondary-button" onClick={() => setConfirmingCancelId(null)}>
                  Never mind
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      <RecommendedTrips existingDestinations={requests.map((r) => r.destination)} />
    </div>
  );
}
