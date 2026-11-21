import { useEffect, useState } from 'react';
import { api } from '../api';
import type { LabComponent } from '../types';

export default function Lab() {
  const [now, setNow] = useState<string | null>(null);
  const [requestId, setRequestId] = useState(1);
  const [component, setComponent] = useState<LabComponent>('flight');
  const [price, setPrice] = useState(1000);
  const [message, setMessage] = useState<string | null>(null);

  function refreshClock() {
    api.labClock().then((c) => setNow(c.now));
  }

  useEffect(() => {
    refreshClock();
  }, []);

  async function handleOverride(e: React.FormEvent) {
    e.preventDefault();
    await api.labOverride(requestId, component, price);
    setMessage(
      `Override set: request #${requestId}, ${component} = ₹${price}. Next "check price now" will use it.`,
    );
  }

  async function handleReset() {
    await api.labReset();
    setMessage('All overrides cleared, clock reset to real time.');
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
        <p className="muted">
          V1's clock is real-time only - advancing it is a V2+ feature, once holds/expiry
          exist to advance past.
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

        <button onClick={handleReset} className="secondary-button">
          Reset all overrides + clock
        </button>

        {message && <p className="muted">{message}</p>}
      </div>
    </div>
  );
}
