import { useEffect, useState } from 'react';
import { api } from '../api';
import type { LabComponent } from '../types';

export default function Lab() {
  const [now, setNow] = useState<string | null>(null);
  const [advanceMinutes, setAdvanceMinutes] = useState(3);
  const [requestId, setRequestId] = useState(1);
  const [component, setComponent] = useState<LabComponent>('flight');
  const [price, setPrice] = useState(1000);
  const [failComponent, setFailComponent] = useState<LabComponent>('hotel');
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
    setMessage(`Clock advanced ${advanceMinutes} minute(s) - any active hold is now that much closer to (or past) expiry.`);
  }

  async function handleOverride(e: React.FormEvent) {
    e.preventDefault();
    await api.labOverride(requestId, component, price);
    setMessage(
      `Override set: request #${requestId}, ${component} = ₹${price}. Next "check price now" will use it.`,
    );
  }

  async function handleFailComponent(e: React.FormEvent) {
    e.preventDefault();
    await api.labFailComponent(requestId, failComponent);
    setMessage(
      `The next booking attempt on request #${requestId} will fail on ${failComponent} - anything booked before it in flight → hotel → cab order will show a compensating cancellation.`,
    );
  }

  async function handleTriggerCycle() {
    const result = await api.labTriggerCycle();
    setMessage(
      `Monitoring cycle ran now (instead of waiting up to 5 real minutes) - checked requests: ${result.checked_request_ids.join(', ') || 'none active'}.`,
    );
  }

  async function handleReset() {
    await api.labReset();
    setMessage('All overrides and failure injections cleared, clock reset to real time.');
    refreshClock();
  }

  return (
    <div className="page">
      <h1>Scenario Lab</h1>
      <p className="muted">
        Dev/demo-only controls - never shown or used by the real traveller-facing
        screens. See docs/DECISIONS.md "Simulation design."
      </p>

      <div className="card">
        <h2>Simulated clock</h2>
        <p>Current time: {now ? new Date(now).toLocaleString() : 'loading...'}</p>
        <form className="form" onSubmit={handleAdvanceClock}>
          <label>
            Advance by (minutes)
            <input
              type="number"
              min={0}
              step="0.5"
              value={advanceMinutes}
              onChange={(e) => setAdvanceMinutes(Number(e.target.value))}
            />
          </label>
          <button type="submit">Advance clock</button>
        </form>
        <p className="muted">
          Fast-forwards past a 2-minute hold in seconds, instead of waiting for real time to pass
          (Sec. 11's "reset and replay").
        </p>
      </div>

      <div className="card">
        <h2>Automatic monitoring cycle</h2>
        <button onClick={handleTriggerCycle}>Trigger cycle now</button>
        <p className="muted">
          Runs the same check every active request normally gets every 5 real minutes - the
          real scheduler job, run on demand instead of waited for.
        </p>
      </div>

      <div className="card">
        <h2>Price override</h2>
        <form className="form" onSubmit={handleOverride}>
          <label>
            Request ID
            <input
              type="number"
              min={1}
              value={requestId}
              onChange={(e) => setRequestId(Number(e.target.value))}
            />
          </label>
          <label>
            Component
            <select
              value={component}
              onChange={(e) => setComponent(e.target.value as LabComponent)}
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
        <h2>Booking failure injection</h2>
        <form className="form" onSubmit={handleFailComponent}>
          <label>
            Request ID
            <input
              type="number"
              min={1}
              value={requestId}
              onChange={(e) => setRequestId(Number(e.target.value))}
            />
          </label>
          <label>
            Component to fail on next booking
            <select
              value={failComponent}
              onChange={(e) => setFailComponent(e.target.value as LabComponent)}
            >
              <option value="flight">Flight</option>
              <option value="hotel">Hotel</option>
              <option value="cab">Cab</option>
            </select>
          </label>
          <button type="submit">Arm failure</button>
        </form>
        <p className="muted">
          One-shot - consumed by the very next booking attempt on this request, then clears
          itself.
        </p>
      </div>

      <button onClick={handleReset} className="secondary-button">
        Reset everything (overrides, failure injection, clock)
      </button>

      {message && <p className="muted">{message}</p>}
    </div>
  );
}
