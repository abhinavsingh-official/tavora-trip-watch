import { useEffect, useState } from 'react';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { LabBookingOutcome, LabComponent, SimulationLogEntryOut, TripRequest } from '../types';

/* labels each card with the scenario it demonstrates, so reviewers don't have to guess */
const SCENARIO_LABELS: Record<string, string> = {
  clock: 'Scenario 3 - hold validity and expiry',
  cycle: 'Scenario 1 & 7 - below-budget alert, monitoring reliability',
  override: 'Scenario 1 & 2 - below-budget trip, price changes before review',
  sharedRoom: 'Scenario 4 - last room contention',
  failComponent: 'Scenario 5 - partial booking failure',
  cancelFailure: 'Scenario 5 (variant) - manual intervention, not a clean rollback',
  restartAfter: 'Scenario 6 - timeout and restart',
};

function formatLogTimestamp(iso: string): string {
  return new Date(iso).toLocaleTimeString();
}

function statusBadgeClass(status: SimulationLogEntryOut['status']): string {
  return `log-status log-status-${status}`;
}

export default function Lab() {
  const { currentUserId, users } = useCurrentUser();
  const [myRequests, setMyRequests] = useState<TripRequest[]>([]);
  const [now, setNow] = useState<string | null>(null);
  const [advanceMinutes, setAdvanceMinutes] = useState('3');
  const [requestId, setRequestId] = useState<number | null>(null);
  const [overrideComponent, setOverrideComponent] = useState<LabComponent>('flight');
  const [price, setPrice] = useState('');
  const [failComponent, setFailComponent] = useState<LabComponent>('hotel');
  const [failOutcome, setFailOutcome] = useState<LabBookingOutcome>('fail');
  const [cancelFailComponent, setCancelFailComponent] = useState<LabComponent>('flight');
  const [restartAfterComponent, setRestartAfterComponent] = useState<LabComponent>('flight');
  const [sharedRoomRequestIds, setSharedRoomRequestIds] = useState('');
  const [sharedRoomCount, setSharedRoomCount] = useState('1');
  const [message, setMessage] = useState<string | null>(null);
  const [log, setLog] = useState<SimulationLogEntryOut[]>([]);
  /* disables every lever while one is running, so a double-click can't fire two overlapping calls */
  const [busy, setBusy] = useState(false);

  function refreshClock() {
    api.labClock().then((c) => setNow(c.now));
  }

  function refreshLog() {
    api.labLog().then(setLog);
  }

  useEffect(() => {
    refreshClock();
    refreshLog();
  }, []);

  /* the target request always follows whichever user the sidebar has selected,
   * so a lever never silently acts on someone else's request */
  useEffect(() => {
    if (currentUserId === null) return;
    api.listRequests(currentUserId).then((reqs) => {
      setMyRequests(reqs);
      setRequestId((prev) => (reqs.some((r) => r.id === prev) ? prev : (reqs[0]?.id ?? null)));
    });
  }, [currentUserId]);

  async function withBusy(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
      /* every lever logs server-side, so just refresh once the action settles */
      refreshLog();
    }
  }

  async function handleAdvanceClock(e: React.FormEvent) {
    e.preventDefault();
    await withBusy(async () => {
      const minutes = Number(advanceMinutes) || 0;
      const result = await api.labAdvanceClock(minutes);
      setNow(result.now);
      setMessage(`Clock moved forward ${minutes} minute(s).`);
    });
  }

  async function handleOverride(e: React.FormEvent) {
    e.preventDefault();
    if (requestId === null) return;
    await withBusy(async () => {
      const value = Number(price) || 0;
      await api.labOverride(requestId, overrideComponent, value);
      setMessage(`Request #${requestId}'s next check will use ₹${value} for ${overrideComponent}.`);
    });
  }

  async function handleFailComponent(e: React.FormEvent) {
    e.preventDefault();
    if (requestId === null) return;
    await withBusy(async () => {
      await api.labFailComponent(requestId, failComponent, failOutcome);
      setMessage(`Request #${requestId}'s next booking will make ${failComponent} ${failOutcome}.`);
    });
  }

  async function handleCancelFailure(e: React.FormEvent) {
    e.preventDefault();
    if (requestId === null) return;
    await withBusy(async () => {
      await api.labCancelFailure(requestId, cancelFailComponent);
      setMessage(`${cancelFailComponent}'s next compensating cancellation on request #${requestId} will itself fail.`);
    });
  }

  async function handleRestartAfter(e: React.FormEvent) {
    e.preventDefault();
    if (requestId === null) return;
    await withBusy(async () => {
      await api.labRestartAfter(requestId, restartAfterComponent);
      setMessage(`Request #${requestId}'s next booking stops right after ${restartAfterComponent} confirms.`);
    });
  }

  async function handleTriggerCycle() {
    await withBusy(async () => {
      const result = await api.labTriggerCycle();
      setMessage(`Ran the cycle now. Checked: ${result.checked_request_ids.join(', ') || 'none active'}.`);
    });
  }

  async function handleMutatePrices() {
    await withBusy(async () => {
      const result = await api.labMutatePrices();
      setMessage(
        `Nudged ${result.flights_mutated} flight(s), ${result.cabs_mutated} cab(s), ${result.hotels_mutated} hotel(s).`,
      );
    });
  }

  async function handleSharedRoomScenario(e: React.FormEvent) {
    e.preventDefault();
    await withBusy(async () => {
      const ids = sharedRoomRequestIds
        .split(',')
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n) && n > 0);
      if (ids.length === 0) {
        setMessage('Enter at least one request ID.');
        return;
      }
      const rooms = Number(sharedRoomCount) || 0;
      await api.labSharedRoomScenario(ids, rooms);
      setMessage(`Requests ${ids.join(', ')} are now racing for ${rooms} room(s). Book each one to see who wins.`);
    });
  }

  async function handleReset() {
    await withBusy(async () => {
      await api.labReset();
      setMessage('Cleared every override, scheduled failure, and the clock.');
      refreshClock();
    });
  }

  async function handleClearLog() {
    await withBusy(async () => {
      await api.labLogClear();
      setMessage('Cleared the activity log.');
    });
  }

  const currentUserName = users.find((u) => u.id === currentUserId)?.name ?? '...';

  return (
    <div className="page lab-page">
      <h1>Scenario Lab</h1>
      <p className="page-intro">
        Dev tools for reviewers - replay the hard cases on demand instead of waiting on real
        time. Every action here logs below.
      </p>

      <div className="card lab-log-card">
        <div className="lab-log-header">
          <h2>Activity log</h2>
          <button onClick={handleClearLog} className="secondary-button" disabled={busy}>
            Clear log
          </button>
        </div>
        {log.length === 0 ? (
          <p className="muted">Nothing logged yet.</p>
        ) : (
          <ul className="lab-log-list">
            {log.map((entry) => (
              <li key={entry.id} className="lab-log-entry">
                <div className="lab-log-entry-top">
                  <span className="lab-log-time">{formatLogTimestamp(entry.created_at)}</span>
                  <span className={statusBadgeClass(entry.status)}>{entry.status}</span>
                  {entry.is_simulated && <span className="log-tag-simulated">simulated</span>}
                  {entry.duration_ms !== null && (
                    <span className="muted">{entry.duration_ms}ms</span>
                  )}
                </div>
                <p>{entry.summary}</p>
                {(entry.flight_name || entry.hotel_name || entry.cab_name) && (
                  <p className="muted lab-log-components">
                    {entry.flight_name && <>Flight: {entry.flight_name} · </>}
                    {entry.hotel_name && <>Hotel: {entry.hotel_name} · </>}
                    {entry.cab_name && <>Cab: {entry.cab_name}</>}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="form lab-shared-field">
        <label>
          Target request (current user: {currentUserName})
          <select
            value={requestId ?? ''}
            onChange={(e) => setRequestId(Number(e.target.value))}
          >
            {myRequests.length === 0 && <option value="">No requests for this user</option>}
            {myRequests.map((r) => (
              <option key={r.id} value={r.id}>
                #{r.id} · {r.origin} → {r.destination}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="card">
        <h2>Simulated clock</h2>
        <p className="scenario-label">{SCENARIO_LABELS.clock}</p>
        <p className="muted">
          Fast-forwards the demo's internal clock, so you don't have to wait real minutes for a
          2-minute offer hold to expire, or for a flight's check-in cutoff to pass.
        </p>
        <p className="muted">Now: {now ? new Date(now).toLocaleString() : 'loading...'}</p>
        <form className="form" onSubmit={handleAdvanceClock}>
          <label>
            Minutes forward
            <input
              type="number"
              min={0}
              step="0.5"
              value={advanceMinutes}
              onFocus={(e) => e.target.select()}
              onChange={(e) => setAdvanceMinutes(e.target.value)}
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Working...' : 'Move clock forward'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Monitoring cycle</h2>
        <p className="scenario-label">{SCENARIO_LABELS.cycle}</p>
        <p className="muted">
          This is the background job that normally runs every 5 real minutes: it re-checks every
          active request's price and sends an alert if one now fits its budget. Prices only
          actually move every few cycles, so "Run cycle now" a handful of times in a row to see a
          real change. "Nudge prices only" moves prices without checking or alerting.
        </p>
        <button onClick={handleTriggerCycle} disabled={busy}>
          {busy ? 'Running...' : 'Run cycle now'}
        </button>
        <button onClick={handleMutatePrices} disabled={busy} className="secondary-button">
          {busy ? 'Working...' : 'Nudge prices only'}
        </button>
      </div>

      <div className="card">
        <h2>Override the next price check</h2>
        <p className="scenario-label">{SCENARIO_LABELS.override}</p>
        <p className="muted">
          Forces one component's price on the target request's very next check only (then clears
          itself). Set a low price here and run a check from the Dashboard to make a below-budget
          alert fire on demand, without waiting for prices to drop naturally.
        </p>
        <form className="form" onSubmit={handleOverride}>
          <label>
            Component
            <select
              value={overrideComponent}
              onChange={(e) => setOverrideComponent(e.target.value as LabComponent)}
            >
              <option value="flight">Flight</option>
              <option value="hotel">Hotel</option>
              <option value="cab">Cab</option>
            </select>
          </label>
          <label>
            Price (INR)
            <input
              type="number"
              min={0}
              placeholder="e.g. 1000"
              value={price}
              onFocus={(e) => e.target.select()}
              onChange={(e) => setPrice(e.target.value)}
            />
          </label>
          <button type="submit" disabled={busy || requestId === null}>
            {busy ? 'Working...' : 'Set override'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Shared room scenario</h2>
        <p className="scenario-label">{SCENARIO_LABELS.sharedRoom}</p>
        <p className="muted">
          Simulates two or more requests competing for the same last hotel rooms. Example: enter{' '}
          <code>1, 2</code> as the request IDs and <code>1</code> as rooms available - now only
          one of those two requests can confirm its hotel. Go pay for each one from its "Your
          bookings" page: whichever you confirm first gets the room and shows "confirmed"; the
          other automatically gets "unavailable" on its hotel, as if someone else had just taken
          the last one.
        </p>
        <form className="form" onSubmit={handleSharedRoomScenario}>
          <label>
            Competing request IDs (comma-separated)
            <input
              type="text"
              placeholder="e.g. 1, 2"
              value={sharedRoomRequestIds}
              onChange={(e) => setSharedRoomRequestIds(e.target.value)}
            />
          </label>
          <label>
            Rooms available
            <input
              type="number"
              min={0}
              value={sharedRoomCount}
              onFocus={(e) => e.target.select()}
              onChange={(e) => setSharedRoomCount(e.target.value)}
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Working...' : 'Set up the race'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Schedule a booking failure</h2>
        <p className="scenario-label">{SCENARIO_LABELS.failComponent}</p>
        <p className="muted">
          Arms a forced outcome for this one component on the target request's very next booking
          attempt only. Set it up here, then go to that request's "Your bookings" page and pay -
          the booking will actually fail that way live, instead of confirming normally. The
          other two components still book as usual.
        </p>
        <form className="form" onSubmit={handleFailComponent}>
          <label>
            Component
            <select
              value={failComponent}
              onChange={(e) => setFailComponent(e.target.value as LabComponent)}
            >
              <option value="flight">Flight</option>
              <option value="hotel">Hotel</option>
              <option value="cab">Cab</option>
            </select>
          </label>
          <label>
            How it fails
            <select
              value={failOutcome}
              onChange={(e) => setFailOutcome(e.target.value as LabBookingOutcome)}
            >
              <option value="fail">Rejected outright</option>
              <option value="unavailable">Inventory gone</option>
              <option value="timeout">Supplier never responds</option>
            </select>
          </label>
          <button type="submit" disabled={busy || requestId === null}>
            {busy ? 'Working...' : 'Schedule this failure'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Schedule a cancellation failure</h2>
        <p className="scenario-label">{SCENARIO_LABELS.cancelFailure}</p>
        <p className="muted">
          Only matters combined with "Schedule a booking failure" above, on a component that
          books after this one (order is flight, then hotel, then cab). Booking flight then hotel
          then failing the cab normally rolls the hotel back. Arm this on "hotel" first, then
          schedule the cab to fail, then pay: the hotel's rollback itself fails, so it's left
          stuck "confirmed" with its supplier - that's the request that ends up on the dashboard
          needing manual follow-up.
        </p>
        <form className="form" onSubmit={handleCancelFailure}>
          <label>
            Component
            <select
              value={cancelFailComponent}
              onChange={(e) => setCancelFailComponent(e.target.value as LabComponent)}
            >
              <option value="flight">Flight</option>
              <option value="hotel">Hotel</option>
              <option value="cab">Cab</option>
            </select>
          </label>
          <button type="submit" disabled={busy || requestId === null}>
            {busy ? 'Working...' : 'Schedule this cancellation failure'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Simulate a restart mid-booking</h2>
        <p className="scenario-label">{SCENARIO_LABELS.restartAfter}</p>
        <p className="muted">
          Simulates the server crashing partway through a booking. Set it up, then pay on the
          target request: booking stops right after this component confirms and the other two
          are left pending. Pay again on the same request and it picks up from the next
          component instead of starting over or double-booking the first one.
        </p>
        <form className="form" onSubmit={handleRestartAfter}>
          <label>
            Stop right after this component confirms
            <select
              value={restartAfterComponent}
              onChange={(e) => setRestartAfterComponent(e.target.value as LabComponent)}
            >
              <option value="flight">Flight</option>
              <option value="hotel">Hotel</option>
              <option value="cab">Cab</option>
            </select>
          </label>
          <button type="submit" disabled={busy || requestId === null}>
            {busy ? 'Working...' : 'Schedule this restart'}
          </button>
        </form>
      </div>

      <button onClick={handleReset} className="secondary-button" disabled={busy}>
        {busy ? 'Working...' : 'Reset everything'}
      </button>

      {message && <p className="muted">{message}</p>}
    </div>
  );
}
