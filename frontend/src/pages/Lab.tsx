import { useEffect, useState } from 'react';
import { api } from '../api';
import type { LabBookingOutcome, LabComponent } from '../types';

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
  const [message, setMessage] = useState<string | null>(null);

  function refreshClock() {
    api.labClock().then((c) => setNow(c.now));
  }

  useEffect(() => {
    refreshClock();
  }, []);

  async function handleAdvanceClock(e: React.FormEvent) {
    e.preventDefault();
    const result = await api.labAdvanceClock(advanceMinutes);
    setNow(result.now);
    setMessage(
      `Clock moved forward ${advanceMinutes} minute(s) - any active hold is now that much closer to (or past) expiry.`,
    );
  }

  async function handleOverride(e: React.FormEvent) {
    e.preventDefault();
    await api.labOverride(requestId, overrideComponent, price);
    setMessage(
      `Request #${requestId}'s next price check will use ₹${price} for ${overrideComponent}, instead of a real supplier call.`,
    );
  }

  async function handleFailComponent(e: React.FormEvent) {
    e.preventDefault();
    await api.labFailComponent(requestId, failComponent, failOutcome);
    const explain = {
      fail: 'fail outright',
      unavailable: 'come back unavailable, as if the inventory had disappeared',
      timeout: "time out - it's left unresolved until you reconcile it on the Booking Result page",
    }[failOutcome];
    setMessage(
      `Request #${requestId}'s next booking attempt will make ${failComponent} ${explain}. Anything already booked before it (flight → hotel → cab order) will show a compensating cancellation.`,
    );
  }

  async function handleCancelFailure(e: React.FormEvent) {
    e.preventDefault();
    await api.labCancelFailure(requestId, cancelFailComponent);
    setMessage(
      `If ${cancelFailComponent} needs to be cancelled during request #${requestId}'s next booking attempt, that cancellation will itself fail - it stays confirmed but flagged for manual follow-up, instead of being falsely marked cancelled.`,
    );
  }

  async function handleRestartAfter(e: React.FormEvent) {
    e.preventDefault();
    await api.labRestartAfter(requestId, restartAfterComponent);
    setMessage(
      `Request #${requestId}'s next booking attempt will stop right after ${restartAfterComponent} is confirmed, as if the app crashed at that moment. Booking the same offer again will pick up where it left off, not start over or duplicate it.`,
    );
  }

  async function handleTriggerCycle() {
    const result = await api.labTriggerCycle();
    setMessage(
      `Ran the monitoring cycle now instead of waiting up to 5 real minutes. Requests checked: ${result.checked_request_ids.join(', ') || 'none active'}.`,
    );
  }

  async function handleReset() {
    await api.labReset();
    setMessage('Cleared every override and scheduled failure, and reset the clock to real time.');
    refreshClock();
  }

  return (
    <div className="page lab-page">
      <h1>Scenario Lab</h1>
      <p className="page-intro">
        Dev/demo-only controls for reviewers - lets you replay the hard cases on demand instead
        of waiting on real time or real supplier conditions. None of this is reachable from, or
        used by, the real traveller-facing screens.
      </p>

      <div className="form lab-shared-field">
        <label>
          Target request ID (used by every lever below)
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
          <button type="submit">Move clock forward</button>
        </form>
        <p className="muted">
          Fast-forwards past a 2-minute hold in seconds, instead of waiting for real time to
          pass.
        </p>
      </div>

      <div className="card">
        <h2>Monitoring cycle</h2>
        <p className="muted">
          Normally runs automatically every 5 real minutes for every active request.
        </p>
        <button onClick={handleTriggerCycle}>Run cycle now</button>
      </div>

      <div className="card">
        <h2>Override the next price check</h2>
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
          <button type="submit">Set override</button>
        </form>
      </div>

      <div className="card">
        <h2>Schedule a booking failure</h2>
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
          <button type="submit">Schedule this failure</button>
        </form>
      </div>

      <div className="card">
        <h2>Schedule a cancellation failure</h2>
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
          <button type="submit">Schedule this cancellation failure</button>
        </form>
      </div>

      <div className="card">
        <h2>Simulate a restart mid-booking</h2>
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
          <button type="submit">Schedule this restart</button>
        </form>
      </div>

      <button onClick={handleReset} className="secondary-button">
        Reset everything (overrides, scheduled failures, clock)
      </button>

      {message && <p className="muted">{message}</p>}
    </div>
  );
}
