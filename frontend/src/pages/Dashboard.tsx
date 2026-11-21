import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { PriceObservation, TripRequest } from '../types';

function StatusBadge({ status }: { status: string }) {
  if (status === 'active') return null; // the normal case - no need to call it out
  return <span className={`status-tag status-${status}`}>{status}</span>;
}

function ObservationSummary({ observation }: { observation: PriceObservation | null }) {
  if (!observation) {
    return <p className="muted">No price checked yet.</p>;
  }

  return (
    <dl className="price-breakdown">
      <div>
        <dt>Flight</dt>
        <dd>
          ₹{observation.flight_outbound_price ?? '-'} + ₹{observation.flight_return_price ?? '-'}
          {observation.flight_status !== 'complete' && (
            <span className="status-tag">{observation.flight_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Hotel</dt>
        <dd>
          ₹{observation.hotel_total_price ?? '-'}
          {observation.hotel_status !== 'complete' && (
            <span className="status-tag">{observation.hotel_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Cabs</dt>
        <dd>
          ₹{observation.cab_outbound_price ?? '-'} + ₹{observation.cab_return_price ?? '-'}
          {observation.cab_status !== 'complete' && (
            <span className="status-tag">{observation.cab_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Taxes/fees</dt>
        <dd>₹{observation.taxes_fees ?? '-'}</dd>
      </div>
      <div className="total-row">
        <dt>Total</dt>
        <dd>
          ₹{observation.total_price ?? '-'}
          <span className={`status-tag status-${observation.status}`}>
            {observation.status}
          </span>
        </dd>
      </div>
    </dl>
  );
}

export default function Dashboard() {
  const { currentUserId } = useCurrentUser();
  const [requests, setRequests] = useState<TripRequest[]>([]);
  const [latest, setLatest] = useState<Record<number, PriceObservation | null>>({});
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadLatest(requestId: number) {
    if (currentUserId === null) return;
    try {
      const observations = await api.listObservations(requestId, currentUserId);
      setLatest((prev) => ({ ...prev, [requestId]: observations[0] ?? null }));
    } catch (err) {
      // Don't let one request's failed history fetch silently reject and
      // disappear - surface it the same way a failed check would.
      setError(err instanceof Error ? err.message : 'Failed to load price history');
    }
  }

  useEffect(() => {
    if (currentUserId === null) return;
    api
      .listRequests(currentUserId)
      .then((fetched) => {
        setRequests(fetched);
        fetched.forEach((r) => loadLatest(r.id));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load requests'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUserId]);

  async function handleCheck(requestId: number) {
    if (currentUserId === null) return;
    setCheckingId(requestId);
    setError(null);
    try {
      await api.checkPrice(requestId, currentUserId);
      await loadLatest(requestId);
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
    }
  }

  return (
    <div className="page">
      <div className="page-header-row">
        <h1>Your requests</h1>
        <Link to="/new" className="button-link">
          + New request
        </Link>
      </div>

      {error && <p className="error-text">{error}</p>}

      {requests.length === 0 && <p className="muted">No requests yet.</p>}

      {requests.map((r) => (
        <div key={r.id} className="card">
          <div className="card-header">
            <h2>
              {r.origin} ⇄ {r.destination} <StatusBadge status={r.status} />
            </h2>
            <span className="muted">
              {r.outbound_date} → {r.return_date} · {r.adults} adults · {r.rooms} room(s) ·
              budget ₹{r.budget_inr}
            </span>
          </div>

          <ObservationSummary observation={latest[r.id] ?? null} />

          <div className="card-actions">
            <button onClick={() => handleCheck(r.id)} disabled={checkingId === r.id || r.status !== 'active'}>
              {checkingId === r.id ? 'Checking...' : 'Check price now'}
            </button>
            <Link to={`/requests/${r.id}/edit`} className="secondary-button">
              Edit
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
            {r.status !== 'cancelled' && (
              <button className="secondary-button" onClick={() => handleStatusChange(r.id, 'cancel')}>
                Cancel
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
