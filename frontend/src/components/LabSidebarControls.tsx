import { useLab } from '../LabContext';

export default function LabSidebarControls() {
  const {
    scenarioRequests,
    requestId,
    setRequestId,
    cancelledCount,
    addSimulatedRequest,
    addBusy,
    shockFraction,
    setShockFraction,
    shockBusy,
    now,
    advanceMinutes,
    setAdvanceMinutes,
    handleAdvanceClock,
    handleTriggerCycle,
    handleMutatePrices,
    overrideComponent,
    setOverrideComponent,
    overridePrice,
    setOverridePrice,
    handleOverride,
    failComponent,
    setFailComponent,
    failOutcome,
    setFailOutcome,
    handleFailComponent,
    cancelFailComponent,
    setCancelFailComponent,
    handleCancelFailure,
    restartAfterComponent,
    setRestartAfterComponent,
    handleRestartAfter,
    sharedRoomIds,
    toggleSharedRoomId,
    sharedRoomCount,
    setSharedRoomCount,
    handleSharedRoomScenario,
    busy,
    message,
    handleReset,
  } = useLab();

  return (
    <div className="sidebar-widget lab-sidebar-controls">
      <h3>Simulation</h3>

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
      <button type="button" className="secondary-button" disabled={addBusy} onClick={addSimulatedRequest}>
        {addBusy ? 'Adding...' : '+ Add a simulated trip'}
      </button>
      {cancelledCount > 0 && (
        <p className="sidebar-tip">{cancelledCount} cancelled - restore from Trash above.</p>
      )}

      <label className="sidebar-field-label lab-shock-slider">
        Shock the market: {shockFraction >= 0 ? '+' : ''}
        {Math.round(shockFraction * 100)}%{shockBusy ? ' · applying' : ''}
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

      <label className="sidebar-field-label">
        Clock: {now ? new Date(now).toLocaleTimeString() : 'loading...'}
        <div className="sidebar-inline-field">
          <input
            type="number"
            min={0}
            step="0.5"
            value={advanceMinutes}
            onFocus={(e) => e.target.select()}
            onChange={(e) => setAdvanceMinutes(e.target.value)}
          />
          <button type="button" className="secondary-button" disabled={busy} onClick={handleAdvanceClock}>
            +min
          </button>
        </div>
      </label>

      <div className="sidebar-inline-field">
        <button type="button" className="secondary-button" disabled={busy} onClick={handleTriggerCycle}>
          Run cycle
        </button>
        <button type="button" className="secondary-button" disabled={busy} onClick={handleMutatePrices}>
          Nudge prices
        </button>
      </div>

      <details className="lab-sidebar-section">
        <summary>Override next check</summary>
        <label className="sidebar-field-label">
          Component
          <select value={overrideComponent} onChange={(e) => setOverrideComponent(e.target.value as typeof overrideComponent)}>
            <option value="flight">Flight</option>
            <option value="hotel">Hotel</option>
            <option value="cab">Cab</option>
          </select>
        </label>
        <div className="sidebar-inline-field">
          <input
            type="number"
            min={0}
            placeholder="₹"
            value={overridePrice}
            onFocus={(e) => e.target.select()}
            onChange={(e) => setOverridePrice(e.target.value)}
          />
          <button type="button" className="secondary-button" disabled={busy || requestId === null} onClick={handleOverride}>
            Set
          </button>
        </div>
      </details>

      <details className="lab-sidebar-section">
        <summary>Booking scenarios</summary>

        <p className="sidebar-tip">Schedule a booking failure</p>
        <label className="sidebar-field-label">
          Component
          <select value={failComponent} onChange={(e) => setFailComponent(e.target.value as typeof failComponent)}>
            <option value="flight">Flight</option>
            <option value="hotel">Hotel</option>
            <option value="cab">Cab</option>
          </select>
        </label>
        <select value={failOutcome} onChange={(e) => setFailOutcome(e.target.value as typeof failOutcome)}>
          <option value="fail">Rejected outright</option>
          <option value="unavailable">Inventory gone</option>
          <option value="timeout">Supplier never responds</option>
        </select>
        <button type="button" className="secondary-button" disabled={busy || requestId === null} onClick={handleFailComponent}>
          Schedule
        </button>

        <p className="sidebar-tip">Schedule a cancellation failure</p>
        <select value={cancelFailComponent} onChange={(e) => setCancelFailComponent(e.target.value as typeof cancelFailComponent)}>
          <option value="flight">Flight</option>
          <option value="hotel">Hotel</option>
          <option value="cab">Cab</option>
        </select>
        <button type="button" className="secondary-button" disabled={busy || requestId === null} onClick={handleCancelFailure}>
          Schedule
        </button>

        <p className="sidebar-tip">Simulate a restart mid-booking</p>
        <select value={restartAfterComponent} onChange={(e) => setRestartAfterComponent(e.target.value as typeof restartAfterComponent)}>
          <option value="flight">Flight</option>
          <option value="hotel">Hotel</option>
          <option value="cab">Cab</option>
        </select>
        <button type="button" className="secondary-button" disabled={busy || requestId === null} onClick={handleRestartAfter}>
          Schedule
        </button>

        <p className="sidebar-tip">Shared room race</p>
        <fieldset className="lab-checkbox-group">
          {scenarioRequests.map((r, i) => (
            <label key={r.id} className="checkbox-label">
              <input type="checkbox" checked={sharedRoomIds.includes(r.id)} onChange={() => toggleSharedRoomId(r.id)} />
              Simulated user {i + 1}
            </label>
          ))}
        </fieldset>
        <div className="sidebar-inline-field">
          <input
            type="number"
            min={0}
            value={sharedRoomCount}
            onFocus={(e) => e.target.select()}
            onChange={(e) => setSharedRoomCount(e.target.value)}
          />
          <button type="button" className="secondary-button" disabled={busy || sharedRoomIds.length < 2} onClick={handleSharedRoomScenario}>
            Race
          </button>
        </div>
      </details>

      {message && <p className="sidebar-tip">{message}</p>}

      <button type="button" className="secondary-button" disabled={busy} onClick={handleReset}>
        Reset everything
      </button>
    </div>
  );
}
