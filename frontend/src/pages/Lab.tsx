import { useEffect, useState } from 'react';
import { api } from '../api';
import type { LabBookingOutcome, LabComponent, SimulationLogEntryOut } from '../types';

/*
 * Maps the assignment's own Sec. 11 scenario numbers to which control
 * below demonstrates them - shown as a label on each card instead of
 * making a reviewer reverse-engineer which raw lever produces which
 * required scenario.
 */
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
  const [now, setNow] = useState<string | null>(null);
  const [advanceMinutes, setAdvanceMinutes] = useState(3);
  const [requestId, setRequestId] = useState(1);
  const [overrideComponent, setOverrideComponent] = useState<LabComponent>('flight');
  const [price, setPrice] = useState(1000);
  const [failComponent, setFailComponent] = useState<LabComponent>('hotel');
  const [failOutcome, setFailOutcome] = useState<LabBookingOutcome>('fail');
  const [cancelFailComponent, setCancelFailComponent] = useState<LabComponent>('flight');
  const [restartAfterComponent, setRestartAfterComponent] = useState<LabComponent>('flight');
  const [sharedRoomRequestIds, setSharedRoomRequestIds] = useState('1,2');
  const [sharedRoomCount, setSharedRoomCount] = useState(1);
  const [message, setMessage] = useState<string | null>(null);
  const [log, setLog] = useState<SimulationLogEntryOut[]>([]);
  /*
   * Audit finding #4: none of these buttons gave any feedback while a real
   * call was in flight - "Run cycle now" in particular can take many real
   * seconds (every active request, real Sabre/Hotelbeds calls), and nothing
   * stopped a double-click from kicking off a second overlapping cycle and
   * spending real supplier quota unnecessarily. One flag disables every
   * lever while any single one is running, not just its own button -
   * overlapping levers (e.g. an override firing mid-cycle) are exactly the
   * kind of non-determinism this page exists to avoid.
   */
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

  async function withBusy(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
      /*
       * Every lever writes to the log (backend side) - refreshing here
       * once, after any action finishes, is what makes this page a
       * running history instead of nine one-shot forms with a single
       * message that disappears on the next click.
       */
      refreshLog();
    }
  }

  async function handleAdvanceClock(e: React.FormEvent) {
    e.preventDefault();
    await withBusy(async () => {
      const result = await api.labAdvanceClock(advanceMinutes);
      setNow(result.now);
      setMessage(
        `Clock moved forward ${advanceMinutes} minute(s) - any active hold is now that much closer to (or past) expiry.`,
      );
    });
  }

  async function handleOverride(e: React.FormEvent) {
    e.preventDefault();
    await withBusy(async () => {
      await api.labOverride(requestId, overrideComponent, price);
      setMessage(
        `Request #${requestId}'s next price check will use ₹${price} for ${overrideComponent}, instead of a real supplier call.`,
      );
    });
  }

  async function handleFailComponent(e: React.FormEvent) {
    e.preventDefault();
    await withBusy(async () => {
      await api.labFailComponent(requestId, failComponent, failOutcome);
      const explain = {
        fail: 'fail outright',
        unavailable: 'come back unavailable, as if the inventory had disappeared',
        timeout: "time out - it's left unresolved until you reconcile it on the Booking Result page",
      }[failOutcome];
      setMessage(
        `Request #${requestId}'s next booking attempt will make ${failComponent} ${explain}. Anything already booked before it (flight → hotel → cab order) will show a compensating cancellation.`,
      );
    });
  }

  async function handleCancelFailure(e: React.FormEvent) {
    e.preventDefault();
    await withBusy(async () => {
      await api.labCancelFailure(requestId, cancelFailComponent);
      setMessage(
        `If ${cancelFailComponent} needs to be cancelled during request #${requestId}'s next booking attempt, that cancellation will itself fail - it stays confirmed but flagged for manual follow-up, instead of being falsely marked cancelled.`,
      );
    });
  }

  async function handleRestartAfter(e: React.FormEvent) {
    e.preventDefault();
    await withBusy(async () => {
      await api.labRestartAfter(requestId, restartAfterComponent);
      setMessage(
        `Request #${requestId}'s next booking attempt will stop right after ${restartAfterComponent} is confirmed, as if the app crashed at that moment. Booking the same offer again will pick up where it left off, not start over or duplicate it.`,
      );
    });
  }

  async function handleTriggerCycle() {
    await withBusy(async () => {
      const result = await api.labTriggerCycle();
      setMessage(
        `Ran the monitoring cycle now instead of waiting up to 5 real minutes. Requests checked: ${result.checked_request_ids.join(', ') || 'none active'}.`,
      );
    });
  }

  async function handleMutatePrices() {
    await withBusy(async () => {
      const result = await api.labMutatePrices();
      setMessage(
        `Nudged prices: ${result.flights_mutated} flight option(s), ${result.cabs_mutated} cab option(s), ${result.hotels_mutated} hotel option(s) moved slightly. Nothing checked/alerted yet - run the cycle separately to see the effect.`,
      );
    });
  }

  async function handleSharedRoomScenario(e: React.FormEvent) {
    e.preventDefault();
    await withBusy(async () => {
      const ids = sharedRoomRequestIds
        .split(',')
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n));
      await api.labSharedRoomScenario(ids, sharedRoomCount);
      setMessage(
        `Requests ${ids.join(', ')} are now racing for ${sharedRoomCount} shared room(s). Book each of them (they need their own held offers) - at most ${sharedRoomCount} will confirm the hotel component; the rest will show a real "unavailable" and a partial status.`,
      );
    });
  }

  async function handleReset() {
    await withBusy(async () => {
      await api.labReset();
      setMessage(
        'Cleared every override, scheduled failure, the shared-room pool, and reset the clock to real time.',
      );
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
      <h1>Scenario Lab</h1>
      <p className="page-intro">
        Dev/demo-only controls for reviewers - lets you replay the hard cases on demand instead
        of waiting on real time or real supplier conditions. None of this is reachable from, or
        used by, the real traveller-facing screens. Every action below writes to the activity
        log, so you can see what actually happened instead of taking it on faith.
      </p>

      <div className="card lab-log-card">
        <div className="lab-log-header">
          <h2>Activity log</h2>
          <button onClick={handleClearLog} className="secondary-button" disabled={busy}>
            Clear log
          </button>
        </div>
        {log.length === 0 ? (
          <p className="muted">
            Nothing logged yet - run a check, a booking, or any lever below to see it appear here.
          </p>
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
          Target request ID (used by every lever below except the shared-room scenario)
          <input
            type="number"
            min={1}
            value={requestId}
            onChange={(e) => setRequestId(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="card">
        <h2>Simulated clock</h2>
        <p className="scenario-label">{SCENARIO_LABELS.clock}</p>
        <p className="muted">Current time: {now ? new Date(now).toLocaleString() : 'loading...'}</p>
        <form className="form" onSubmit={handleAdvanceClock}>
          <label>
            Move forward by (minutes)
            <input
              type="number"
              min={0}
              step="0.5"
              value={advanceMinutes}
              onChange={(e) => setAdvanceMinutes(Number(e.target.value))}
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Working...' : 'Move clock forward'}
          </button>
        </form>
        <p className="muted">
          Fast-forwards past a 2-minute hold in seconds, instead of waiting for real time to
          pass.
        </p>
      </div>

      <div className="card">
        <h2>Monitoring cycle</h2>
        <p className="scenario-label">{SCENARIO_LABELS.cycle}</p>
        <p className="muted">
          Normally runs automatically every 5 real minutes for every active request, nudging
          prices first so repeated checks show real movement.
        </p>
        <button onClick={handleTriggerCycle} disabled={busy}>
          {busy ? 'Running...' : 'Run cycle now'}
        </button>
        <button onClick={handleMutatePrices} disabled={busy} className="secondary-button">
          {busy ? 'Working...' : 'Nudge prices only (no check yet)'}
        </button>
      </div>

      <div className="card">
        <h2>Override the next price check</h2>
        <p className="scenario-label">{SCENARIO_LABELS.override}</p>
        <p className="muted">
          Makes the target request's next "check price now" use a price you choose, instead of
          calling the real supplier.
        </p>
        <form className="form" onSubmit={handleOverride}>
          <label>
            Component to override
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
              value={price}
              onChange={(e) => setPrice(Number(e.target.value))}
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Working...' : 'Set override'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Shared room scenario</h2>
        <p className="scenario-label">{SCENARIO_LABELS.sharedRoom}</p>
        <p className="muted">
          Registers a small set of requests against one shared, finite room count - at most
          that many can successfully confirm their hotel component; the rest see a real
          "unavailable" and a partial booking, exactly like two travellers racing for the same
          last room.
        </p>
        <form className="form" onSubmit={handleSharedRoomScenario}>
          <label>
            Competing request IDs (comma-separated)
            <input
              type="text"
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
              onChange={(e) => setSharedRoomCount(Number(e.target.value))}
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
          One-shot - applies to the target request's very next booking attempt, then clears
          itself.
        </p>
        <form className="form" onSubmit={handleFailComponent}>
          <label>
            Component that should fail
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
            How it should fail
            <select
              value={failOutcome}
              onChange={(e) => setFailOutcome(e.target.value as LabBookingOutcome)}
            >
              <option value="fail">Rejected outright by the supplier</option>
              <option value="unavailable">Inventory disappeared (no longer available)</option>
              <option value="timeout">Supplier never responds (needs reconciliation)</option>
            </select>
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Working...' : 'Schedule this failure'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Schedule a cancellation failure</h2>
        <p className="scenario-label">{SCENARIO_LABELS.cancelFailure}</p>
        <p className="muted">
          Combine with the booking failure above - e.g. fail the hotel, and also make the
          flight's compensating cancellation fail, to see "manual_intervention" rather than a
          clean rollback.
        </p>
        <form className="form" onSubmit={handleCancelFailure}>
          <label>
            Component whose cancellation should fail
            <select
              value={cancelFailComponent}
              onChange={(e) => setCancelFailComponent(e.target.value as LabComponent)}
            >
              <option value="flight">Flight</option>
              <option value="hotel">Hotel</option>
              <option value="cab">Cab</option>
            </select>
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Working...' : 'Schedule this cancellation failure'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Simulate a restart mid-booking</h2>
        <p className="scenario-label">{SCENARIO_LABELS.restartAfter}</p>
        <p className="muted">
          One-shot - the next booking attempt stops right after the chosen component is
          confirmed, as if the app crashed there. Booking the same offer again resumes it from
          the next component instead of starting over or duplicating it.
        </p>
        <form className="form" onSubmit={handleRestartAfter}>
          <label>
            Stop right after this component is confirmed
            <select
              value={restartAfterComponent}
              onChange={(e) => setRestartAfterComponent(e.target.value as LabComponent)}
            >
              <option value="flight">Flight</option>
              <option value="hotel">Hotel</option>
              <option value="cab">Cab</option>
            </select>
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Working...' : 'Schedule this restart'}
          </button>
        </form>
      </div>

      <button onClick={handleReset} className="secondary-button" disabled={busy}>
        {busy ? 'Working...' : 'Reset everything (overrides, scheduled failures, shared rooms, clock)'}
      </button>

      {message && <p className="muted">{message}</p>}
    </div>
  );
}
