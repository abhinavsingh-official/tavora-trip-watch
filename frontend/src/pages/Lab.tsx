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

function Steps({ items }: { items: string[] }) {
  return (
    <ol className="lab-steps">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ol>
  );
}

export default function Lab() {
  const { users, setCurrentUserId } = useCurrentUser();
  const [scenarioRequests, setScenarioRequests] = useState<TripRequest[]>([]);
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

  const scenarioUser = users.find((u) => u.name === 'Scenario');

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

  /*
   * Every lever here always acts on the dedicated "Scenario" user's own
   * requests, never on whichever real demo user the sidebar currently has
   * selected - so running a scenario can never quietly change what a
   * reviewer is looking at under User A/B/C.
   */
  useEffect(() => {
    if (scenarioUser === undefined) return;
    api.listRequests(scenarioUser.id).then((reqs) => {
      setScenarioRequests(reqs);
      setRequestId((prev) => (reqs.some((r) => r.id === prev) ? prev : (reqs[0]?.id ?? null)));
      if (reqs.length > 0) {
        setSharedRoomRequestIds((prev) => prev || reqs.map((r) => r.id).join(', '));
      }
    });
  }, [scenarioUser]);

  function handleViewAsScenario() {
    if (scenarioUser !== undefined) setCurrentUserId(scenarioUser.id);
  }

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

  return (
    <div className="page lab-page">
      <h1>Simulation</h1>
      <p className="page-intro">
        Runs demo scenarios against a dedicated "Scenario" user, not your own test data. Set one
        up below, then switch to Scenario to watch it happen.
      </p>

      <button type="button" onClick={handleViewAsScenario} disabled={scenarioUser === undefined}>
        View as Scenario
      </button>

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
          Target request (Scenario user)
          <select
            value={requestId ?? ''}
            onChange={(e) => setRequestId(Number(e.target.value))}
          >
            {scenarioRequests.length === 0 && <option value="">Loading...</option>}
            {scenarioRequests.map((r) => (
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
        <Steps
          items={[
            'Fast-forwards the demo\'s internal clock by the minutes below.',
            'Use it to skip past a 2-minute offer hold expiring, or a flight\'s check-in cutoff, without waiting in real time.',
          ]}
        />
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
        <Steps
          items={[
            'This is the background job that normally runs every 5 real minutes: it re-checks every active request\'s price and alerts if one now fits its budget.',
            'Prices only actually move every few cycles, so click "Run cycle now" a handful of times in a row to see a real change.',
            '"Nudge prices only" moves prices without checking or alerting, if you just want to move the market first.',
          ]}
        />
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
        <Steps
          items={[
            'Set a component and a low price below, then click "Set override".',
            'Go to the Dashboard and run "Check price now" on the target request above - that one check uses your forced price, then the override clears itself.',
            'If the new total is under budget, an alert appears under the bell icon.',
          ]}
        />
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
        <Steps
          items={[
            'Pre-filled with the Scenario user\'s own two requests, both searching Goa on the same dates - enter how many rooms are actually available (try 1) and click "Set up the race".',
            'Open "Your bookings" for each of those two requests and pay.',
            'Whichever you confirm first gets the room and shows "confirmed"; the other automatically gets "unavailable" on its hotel, as if someone else had just taken the last one.',
          ]}
        />
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
        <Steps
          items={[
            'Pick a component and how it should fail below, then click "Schedule this failure".',
            'Open "Your bookings" for the target request above and pay.',
            'That one component fails live, that way, instead of confirming - the other two still book normally.',
          ]}
        />
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
        <Steps
          items={[
            'Only matters paired with "Schedule a booking failure" above, on a component that books after this one (order is flight, then hotel, then cab).',
            'Pick "hotel" below and click "Schedule this cancellation failure".',
            'Then go up to "Schedule a booking failure", pick "cab", and schedule that too.',
            'Open "Your bookings" and pay: the cab fails, which normally rolls the hotel back - instead that rollback itself fails, leaving the hotel stuck "confirmed" with its supplier. That\'s the request that shows up needing manual follow-up on the Dashboard.',
          ]}
        />
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
        <Steps
          items={[
            'Pick a component below and click "Schedule this restart".',
            'Open "Your bookings" for the target request above and pay - booking stops right after that component confirms, as if the server crashed, and the other two are left pending.',
            'Pay again on the same request: it picks up from the next component instead of starting over or double-booking the first one.',
          ]}
        />
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
