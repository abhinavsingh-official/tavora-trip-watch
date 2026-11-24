import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { PriceObservation, TripRequest } from '../types';

function StatusBadge({ status }: { status: string }) {
  if (status === 'active') return null; // the normal case - no need to call it out
  return <span className={`status-tag status-${status}`}>{status}</span>;
}

// Sec. 06: "Show latest valid total, lowest observed valid total and a
// price-history chart." Previously only the single latest check (valid or
// not) was ever shown - no lowest-ever total, no chart at all. Plain inline
// SVG, no charting library - consistent with the rest of this project's
// "no new dependency" discipline, and Sec. 10/15's "polish is secondary".
function PriceHistoryChart({
  observations,
  budget,
}: {
  observations: PriceObservation[];
  budget: number;
}) {
  const valid = observations
    .filter((o) => o.status === 'complete' && o.total_price !== null)
    .slice()
    .sort((a, b) => new Date(a.observed_at).getTime() - new Date(b.observed_at).getTime());

  if (valid.length < 2) {
    return (
      <p className="muted">
        Not enough complete checks yet for a history chart - needs at least 2.
      </p>
    );
  }

  const width = 480;
  const height = 120;
  const padding = 8;
  const totals = valid.map((o) => o.total_price as number);
  const minY = Math.min(...totals, budget);
  const maxY = Math.max(...totals, budget);
  const spanY = maxY - minY || 1;

  const x = (i: number) => padding + (i / (valid.length - 1)) * (width - padding * 2);
  const y = (v: number) => height - padding - ((v - minY) / spanY) * (height - padding * 2);

  const linePoints = totals.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const budgetY = y(budget);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="price-history-chart"
      role="img"
      aria-label="Price history chart"
    >
      <line
        x1={padding}
        y1={budgetY}
        x2={width - padding}
        y2={budgetY}
        stroke="var(--color-text-muted)"
        strokeDasharray="4 3"
        strokeWidth={1}
      />
      <polyline fill="none" stroke="var(--color-accent)" strokeWidth={2} points={linePoints} />
      {totals.map((v, i) => (
        <circle key={i} cx={x(i)} cy={y(v)} r={3} fill="var(--color-accent)" />
      ))}
    </svg>
  );
}

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

  // Audit finding #1: editing a request (budget, dates, occupancy...) never
  // touches its past observations - they're historical, append-only - so
  // without this, nothing on screen could tell "this total reflects the
  // trip as it is now" from "this total predates your last edit".
  const isStale = new Date(latest.observed_at) < new Date(requestUpdatedAt);

  return (
    <>
      {isStale && (
        <p className="price-change-note">
          This total was checked before your last edit - it may no longer reflect the current
          trip. Run "Check price now" for a current total.
        </p>
      )}
      <dl className="price-breakdown">
      <div>
        <dt>Flight</dt>
        <dd>
          ₹{latest.flight_outbound_price ?? '-'} + ₹{latest.flight_return_price ?? '-'}
          {latest.flight_status !== 'complete' && (
            <span className="status-tag">{latest.flight_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Hotel</dt>
        <dd>
          ₹{latest.hotel_total_price ?? '-'}
          {latest.hotel_status !== 'complete' && (
            <span className="status-tag">{latest.hotel_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Cabs</dt>
        <dd>
          ₹{latest.cab_outbound_price ?? '-'} + ₹{latest.cab_return_price ?? '-'}
          {latest.cab_status !== 'complete' && (
            <span className="status-tag">{latest.cab_status}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Taxes/fees</dt>
        <dd>₹{latest.taxes_fees ?? '-'}</dd>
      </div>
      <div className="total-row">
        <dt>Latest check</dt>
        <dd>
          ₹{latest.total_price ?? '-'}
          <span className={`status-tag status-${latest.status}`}>{latest.status}</span>
        </dd>
      </div>
      {latestValid && latestValid.id !== latest.id && (
        <div>
          <dt>Latest valid total</dt>
          <dd>₹{latestValid.total_price}</dd>
        </div>
      )}
      {lowestValid !== null && (
        <div>
          <dt>Lowest observed (valid)</dt>
          <dd>₹{lowestValid}</dd>
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
  // Audit finding #2: Cancel is irreversible (a cancelled request can never
  // be reactivated) and used to fire instantly, no confirmation, right next
  // to Pause/Resume/Edit - a single misclick permanently killed a request
  // with no recovery path. Tracks which card is mid-confirmation, if any.
  const [confirmingCancelId, setConfirmingCancelId] = useState<number | null>(null);

  async function loadHistory(requestId: number) {
    if (currentUserId === null) return;
    try {
      const observations = await api.listObservations(requestId, currentUserId);
      setHistory((prev) => ({ ...prev, [requestId]: observations }));
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
        fetched.forEach((r) => loadHistory(r.id));
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

  return (
    <div className="page">
      <div className="page-header-row">
        <h1>Your requests</h1>
        <Link to="/new" className="button-link">
          + New request
        </Link>
      </div>
      <p className="page-intro">
        Every request here is checked automatically every 5 minutes (and on demand below) -
        current and historical totals, and an alert the moment a complete package meets budget.
      </p>

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

          <ObservationSummary
            observations={history[r.id] ?? []}
            requestUpdatedAt={r.updated_at}
            budget={r.budget_inr}
          />

          <div className="card-actions">
            <button onClick={() => handleCheck(r.id)} disabled={checkingId === r.id || r.status !== 'active'}>
              {checkingId === r.id ? 'Checking...' : 'Check price now'}
            </button>
            {/* Audit finding #10: a cancelled request can never be
                reactivated, so editing one was a real, saveable, completely
                inert action - hidden here rather than left as a dead end. */}
            {r.status !== 'cancelled' && (
              <Link to={`/requests/${r.id}/edit`} className="button-link secondary-button">
                Edit
              </Link>
            )}
            <Link to={`/requests/${r.id}/story`} className="button-link secondary-button">
              View trip story
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
          </div>

          {confirmingCancelId === r.id && (
            <div className="price-change-note">
              <p>Cancel this request? This can't be undone - a cancelled request can never be reactivated or edited.</p>
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
    </div>
  );
}
