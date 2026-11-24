import { useLab } from '../LabContext';

/*
 * The Simulation page's "which simulated user / which preset" controls -
 * moved here from the Lab page itself, so the sidebar is where you set up
 * the scenario and the main page is entirely the result (bookings,
 * notifications, timeline), not a settings card sitting on top of it.
 */
export default function LabSidebarControls() {
  const { scenarioRequests, requestId, setRequestId, cancelledCount, addSimulatedRequest, addBusy } =
    useLab();

  return (
    <div className="sidebar-widget lab-sidebar-controls">
      <h3>Simulation</h3>
      <p className="sidebar-tip">
        Everything on this page acts on the simulated user picked below - a sandbox trip, never a
        real traveler's data.
      </p>

      <label className="sidebar-field-label">
        Simulated user
        <select value={requestId ?? ''} onChange={(e) => setRequestId(Number(e.target.value))}>
          {scenarioRequests.length === 0 && <option value="">Loading...</option>}
          {scenarioRequests.map((r, i) => (
            <option key={r.id} value={r.id}>
              Simulated user {i + 1} · {r.origin} → {r.destination}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="secondary-button"
        disabled={addBusy}
        onClick={addSimulatedRequest}
        title="Adds a new simulated trip - never touches a real user's requests"
      >
        {addBusy ? 'Adding...' : '+ Add a simulated trip'}
      </button>

      {cancelledCount > 0 && (
        <p className="sidebar-tip">
          {cancelledCount} cancelled and hidden - restore from the Trash icon above.
        </p>
      )}
    </div>
  );
}
