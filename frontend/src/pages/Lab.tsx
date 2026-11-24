import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { formatInr } from '../format';
import { useLab } from '../LabContext';
import TripDirectoryBrowser from '../components/TripDirectoryBrowser';
import type {
  BookingAttempt,
  LabBookingOutcome,
  LabComponent,
  Notification,
  PriceObservation,
  SimulationLogEntryOut,
  TimelineEvent,
  TripDirectory,
} from '../types';

/* The Timeline and Simulated notifications lists are a real, scoped
   record - but left unbounded they grow forever as routine checks pile
   up. Capping what's shown keeps the page readable without hiding data
   (nothing is deleted, just not all rendered at once). */
const MAX_TIMELINE_ROWS = 8;
const MAX_NOTIFICATION_ROWS = 5;

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

function SectionLabel({ children }: { children: string }) {
  return <div className="lab-section-label">{children}</div>;
}

export default function Lab() {
  const { requestId, scenarioUserId, scenarioRequests } = useLab();
  const [now, setNow] = useState<string | null>(null);
  const [advanceMinutes, setAdvanceMinutes] = useState('3');
  const [overrideComponent, setOverrideComponent] = useState<LabComponent>('flight');
  const [price, setPrice] = useState('');
  const [failComponent, setFailComponent] = useState<LabComponent>('hotel');
  const [failOutcome, setFailOutcome] = useState<LabBookingOutcome>('fail');
  const [cancelFailComponent, setCancelFailComponent] = useState<LabComponent>('flight');
  const [restartAfterComponent, setRestartAfterComponent] = useState<LabComponent>('flight');
  const [sharedRoomIds, setSharedRoomIds] = useState<number[]>([]);
  const [sharedRoomCount, setSharedRoomCount] = useState('1');
  const [message, setMessage] = useState<string | null>(null);
  const [log, setLog] = useState<SimulationLogEntryOut[]>([]);
  /* disables every lever while one is running, so a double-click can't fire two overlapping calls */
  const [busy, setBusy] = useState(false);

  /* Everything needed to see a scenario's effect without leaving this page */
  const [latestObservation, setLatestObservation] = useState<PriceObservation | null>(null);
  const [simulatedNotifications, setSimulatedNotifications] = useState<Notification[]>([]);
  const [booking, setBooking] = useState<BookingAttempt | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [directory, setDirectory] = useState<TripDirectory | null>(null);
  const [panelBusy, setPanelBusy] = useState(false);

  /* The shock slider - a direct, exact, signed % move applied to this
     trip's own market the moment it settles, instead of a value you type
     in and then have to separately go click "check" to see take effect. */
  const [shockFraction, setShockFraction] = useState(0);
  const [shockBusy, setShockBusy] = useState(false);
  const shockSkipRef = useRef(true);

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

  function refreshTargetPanel() {
    if (requestId === null || scenarioUserId === null) return;
    api
      .listObservations(requestId, scenarioUserId)
      .then((obs) => setLatestObservation(obs[0] ?? null));
    api
      .listNotifications(scenarioUserId)
      .then((all) => setSimulatedNotifications(all.filter((n) => n.request_id === requestId)));
    api.getRequestTimeline(requestId, scenarioUserId).then(setTimeline);
    api.getTripDirectory(requestId, scenarioUserId).then(setDirectory).catch(() => setDirectory(null));
  }

  useEffect(() => {
    setBooking(null);
    setShockFraction(0);
    shockSkipRef.current = true;
    refreshTargetPanel();
    /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [requestId, scenarioUserId]);

  useEffect(() => {
    if (requestId === null || scenarioUserId === null) return;
    if (shockSkipRef.current) {
      /* the reset above (switching simulated user) lands here too - don't
         fire a real shock for that, only for an actual slider drag */
      shockSkipRef.current = false;
      return;
    }
    setShockBusy(true);
    const timer = window.setTimeout(() => {
      api
        .labShockAndCheck(requestId, shockFraction)
        .then((observation) => {
          setLatestObservation(observation);
          refreshTargetPanel();
          refreshLog();
          setMessage(
            `Shocked this trip's market ${shockFraction >= 0 ? '+' : ''}${Math.round(shockFraction * 100)}% - total now ${
              observation.total_price !== null ? `₹${formatInr(observation.total_price)}` : 'unavailable'
            }.`,
          );
        })
        .finally(() => setShockBusy(false));
    }, 350);
    return () => window.clearTimeout(timer);
    /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [shockFraction]);

  async function handleCheckPrice() {
    if (requestId === null || scenarioUserId === null) return;
    setPanelBusy(true);
    try {
      const observation = await api.checkPrice(requestId, scenarioUserId);
      setLatestObservation(observation);
      refreshTargetPanel();
      refreshLog();
      setMessage(`Checked - total ${observation.total_price !== null ? `₹${formatInr(observation.total_price)}` : 'unavailable'} (${observation.status}).`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Check failed');
    } finally {
      setPanelBusy(false);
    }
  }

  async function handleBookNow() {
    if (requestId === null) return;
    setPanelBusy(true);
    try {
      const result = await api.labBookNow(requestId);
      setBooking(result);
      refreshTargetPanel();
      refreshLog();
      setMessage(`Booking attempt: ${result.aggregate_status}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Booking failed');
    } finally {
      setPanelBusy(false);
    }
  }

  async function handleReconcile(outcome: 'confirmed' | 'failed') {
    if (!booking || scenarioUserId === null) return;
    setPanelBusy(true);
    try {
      const result = await api.reconcileBooking(booking.id, scenarioUserId, outcome);
      setBooking(result);
      refreshTargetPanel();
      refreshLog();
    } finally {
      setPanelBusy(false);
    }
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

  function toggleSharedRoomId(id: number) {
    setSharedRoomIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function handleSharedRoomScenario(e: React.FormEvent) {
    e.preventDefault();
    if (sharedRoomIds.length < 2) {
      setMessage('Check at least two requests to race against each other.');
      return;
    }
    await withBusy(async () => {
      const rooms = Number(sharedRoomCount) || 0;
      await api.labSharedRoomScenario(sharedRoomIds, rooms);
      setMessage(
        `Requests ${sharedRoomIds.join(', ')} are now racing for ${rooms} room(s). Book each one to see who wins.`,
      );
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
        A self-contained sandbox, separate from your real demo data - pick or add a simulated user
        in the sidebar, then use the levers below. Nothing here ever touches User A/B/C.
      </p>

      <div className="card">
        <h2>Price, notifications &amp; booking</h2>
        <p className="muted">
          Pick the simulated user in the sidebar first. Drag the slider below for an immediate,
          guaranteed price move on this trip - no separate "now go click check" step.{' '}
          <strong>Check price now</strong> re-reads the price as-is (same as the Dashboard's
          button). <strong>Book now (simulated)</strong> skips straight to paying.
        </p>

        <label className="sidebar-field-label lab-shock-slider">
          Shock this trip's market: {shockFraction >= 0 ? '+' : ''}
          {Math.round(shockFraction * 100)}%{shockBusy ? ' · applying...' : ''}
          <input
            type="range"
            min={-60}
            max={60}
            step={5}
            value={Math.round(shockFraction * 100)}
            disabled={requestId === null}
            onChange={(e) => setShockFraction(Number(e.target.value) / 100)}
          />
        </label>
        <p className="muted">
          Moves every flight/hotel option on this exact route+dates, and every cab, to that
          percentage above or below its normal price - applied and checked the moment you let go.
        </p>

        <div className="card-actions">
          <button type="button" onClick={handleCheckPrice} disabled={panelBusy || requestId === null}>
            {panelBusy ? 'Working...' : 'Check price now'}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={handleBookNow}
            disabled={panelBusy || requestId === null}
          >
            {panelBusy ? 'Working...' : 'Book now (simulated)'}
          </button>
        </div>

        {latestObservation && (
          <p className="muted">
            Latest check: {latestObservation.total_price !== null ? `₹${formatInr(latestObservation.total_price)}` : 'unavailable'}{' '}
            ({latestObservation.status})
          </p>
        )}

        {booking && (
          <>
            <h3>Booking attempt</h3>
            <p className="muted">What the simulated "Book now" click actually did to each part of the trip.</p>
            <div className="booking-component-row">
              <span>Flight</span>
              <span className={`status-tag status-${booking.flight_status}`}>{booking.flight_status}</span>
            </div>
            <div className="booking-component-row">
              <span>Hotel</span>
              <span className={`status-tag status-${booking.hotel_status}`}>{booking.hotel_status}</span>
            </div>
            <div className="booking-component-row">
              <span>Cab</span>
              <span className={`status-tag status-${booking.cab_status}`}>{booking.cab_status}</span>
            </div>
            <p className="muted">
              Overall: <span className={`status-tag status-${booking.aggregate_status}`}>{booking.aggregate_status}</span>
            </p>
            {booking.aggregate_status === 'needs_reconciliation' && (
              <div className="card-actions">
                <button type="button" disabled={panelBusy} onClick={() => handleReconcile('confirmed')}>
                  Reconcile: it was actually booked
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={panelBusy}
                  onClick={() => handleReconcile('failed')}
                >
                  Reconcile: it was never booked
                </button>
              </div>
            )}
          </>
        )}

        <h3>Simulated notifications</h3>
        <p className="muted">
          Price alerts raised for this simulated user - same alert you'd see under the bell icon,
          scoped to this one request. "New" means not opened yet.
        </p>
        {simulatedNotifications.length === 0 ? (
          <p className="muted">None yet - run "Check price now" until one shows up here.</p>
        ) : (
          <ul className="lab-mini-list">
            {simulatedNotifications.slice(0, MAX_NOTIFICATION_ROWS).map((n) => (
              <li key={n.id}>
                <span>
                  {n.origin} → {n.destination}: ₹{formatInr(n.total_price)}
                </span>
                <span className="muted">
                  {n.reviewed_at ? 'reviewed' : 'new'}
                  {n.held_until ? ' · held' : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
        {simulatedNotifications.length > MAX_NOTIFICATION_ROWS && (
          <p className="muted">
            + {simulatedNotifications.length - MAX_NOTIFICATION_ROWS} earlier alert(s) not shown.
          </p>
        )}

        <h3>Timeline</h3>
        <p className="muted">
          Everything that's happened to this simulated user, in order: price checks, alerts, and
          booking attempts.
        </p>
        {timeline.length === 0 ? (
          <p className="muted">Nothing has happened for this simulated user yet.</p>
        ) : (
          <ul className="timeline">
            {timeline.slice(-MAX_TIMELINE_ROWS).map((event, i) => (
              <li key={i} className={`timeline-event timeline-${event.type}`}>
                <span className="muted">{new Date(event.at).toLocaleTimeString()}</span> —{' '}
                {event.summary}
              </li>
            ))}
          </ul>
        )}
        {timeline.length > MAX_TIMELINE_ROWS && (
          <p className="muted">Showing the most recent {MAX_TIMELINE_ROWS} of {timeline.length} events.</p>
        )}

        {directory && (
          <>
            <h3>Browse this trip's options</h3>
            <p className="muted">
              Looking around here is just for context - it never changes what "Book now" actually
              books, which always uses the cheapest eligible option (marked "Cheapest found").
            </p>
            <TripDirectoryBrowser directory={directory} />
          </>
        )}
      </div>

      <SectionLabel>Time &amp; pricing</SectionLabel>

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
            'Click "Check price now" in the panel above - that one check uses your forced price, then the override clears itself.',
            'If the new total is under budget, an alert appears there under "Simulated notifications".',
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

      <SectionLabel>Booking scenarios</SectionLabel>

      <div className="card">
        <h2>Shared room scenario</h2>
        <p className="scenario-label">{SCENARIO_LABELS.sharedRoom}</p>
        <Steps
          items={[
            'Check two of the Scenario user\'s own requests below, enter how many rooms are actually available (try 1), and click "Set up the race".',
            'Switch "Simulated user" above to each of those two requests in turn and click "Book now" each time.',
            'Whichever you confirm first gets the room and shows "confirmed"; the other automatically gets "unavailable" on its hotel, as if someone else had just taken the last one.',
          ]}
        />
        <form className="form" onSubmit={handleSharedRoomScenario}>
          <fieldset className="lab-checkbox-group">
            <legend>Competing simulated users</legend>
            {scenarioRequests.map((r, i) => (
              <label key={r.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={sharedRoomIds.includes(r.id)}
                  onChange={() => toggleSharedRoomId(r.id)}
                />
                Simulated user {i + 1} · {r.origin} → {r.destination}
              </label>
            ))}
          </fieldset>
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
          <button type="submit" disabled={busy || sharedRoomIds.length < 2}>
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
            'Click "Book now" in the panel above.',
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
            'Click "Book now" in the panel above: the cab fails, which normally rolls the hotel back - instead that rollback itself fails, leaving the hotel stuck "confirmed" with its supplier, shown right there as "manual_intervention". That\'s the one real ops can\'t resolve automatically - it also shows up on the Dashboard\'s "Needs attention".',
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
            'Click "Book now" in the panel above - booking stops right after that component confirms, as if the server crashed, and the other two are left pending.',
            'Click "Book now" again on the same simulated user: it picks up from the next component instead of starting over or double-booking the first one.',
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

      <div className="card lab-log-card">
        <div className="lab-log-header">
          <h2>Activity log</h2>
          <button onClick={handleClearLog} className="secondary-button" disabled={busy}>
            Clear log
          </button>
        </div>
        <p className="muted">
          Only shows Scenario's own activity, not anyone else's real traffic - this is the record
          of what the buttons above actually did, in order.
        </p>
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
    </div>
  );
}
