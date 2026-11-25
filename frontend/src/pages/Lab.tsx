import { useEffect, useState } from 'react';
import { api } from '../api';
import { formatInr } from '../format';
import { useLab } from '../LabContext';
import PriceHistoryChart from '../components/PriceHistoryChart';
import TripDirectoryBrowser from '../components/TripDirectoryBrowser';
import type {
  BookingAttempt,
  Notification,
  PriceObservation,
  SharedRoomStatus,
  SimulationLogEntryOut,
  TimelineEvent,
  TripDirectory,
  TripRequest,
} from '../types';

const MAX_NOTIFICATION_ROWS = 5;

function statusBadgeClass(status: SimulationLogEntryOut['status']): string {
  return `log-status log-status-${status}`;
}

export default function Lab() {
  const { requestId, scenarioUserId, scenarioRequests, version, log } = useLab();

  const [observations, setObservations] = useState<PriceObservation[]>([]);
  const [simulatedNotifications, setSimulatedNotifications] = useState<Notification[]>([]);
  const [booking, setBooking] = useState<BookingAttempt | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [directory, setDirectory] = useState<TripDirectory | null>(null);
  const [showBrowser, setShowBrowser] = useState(false);
  const [panelBusy, setPanelBusy] = useState(false);
  const [panelMessage, setPanelMessage] = useState<string | null>(null);
  const [raceStatus, setRaceStatus] = useState<SharedRoomStatus | null>(null);

  const request: TripRequest | undefined = scenarioRequests.find((r) => r.id === requestId);
  const latest = observations[0] ?? null;

  function labelFor(reqId: number): string {
    const i = scenarioRequests.findIndex((r) => r.id === reqId);
    return i >= 0 ? `Simulated user ${i + 1}` : `Request #${reqId}`;
  }

  function refresh() {
    if (requestId === null || scenarioUserId === null) return;
    api.listObservations(requestId, scenarioUserId).then(setObservations);
    api
      .listNotifications(scenarioUserId)
      .then((all) => setSimulatedNotifications(all.filter((n) => n.request_id === requestId)));
    api.getRequestTimeline(requestId, scenarioUserId).then(setTimeline);
    api.getTripDirectory(requestId, scenarioUserId).then(setDirectory).catch(() => setDirectory(null));
    api.labSharedRoomStatus().then(setRaceStatus);
  }

  useEffect(() => {
    setBooking(null);
    setShowBrowser(false);
    refresh();
    /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [requestId, scenarioUserId, version]);

  async function handleCheckPrice() {
    if (requestId === null || scenarioUserId === null) return;
    setPanelBusy(true);
    try {
      await api.checkPrice(requestId, scenarioUserId);
      refresh();
    } catch (err) {
      setPanelMessage(err instanceof Error ? err.message : 'Check failed');
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
      refresh();
    } catch (err) {
      setPanelMessage(err instanceof Error ? err.message : 'Booking failed');
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
      refresh();
    } finally {
      setPanelBusy(false);
    }
  }

  return (
    <div className="page lab-page">
      <h1>Simulation</h1>
      <p className="page-intro">
        A sandbox, separate from your real demo data - the sidebar sets up the scenario, this page
        shows what happened.
      </p>

      <div className="lab-layout">
        <div className="lab-main-column">
          <div className="card">
            <h2>Price breakdown</h2>
            {latest ? (
              <dl className="price-breakdown">
                <div>
                  <dt>Flight</dt>
                  <dd>₹{formatInr(latest.flight_outbound_price)} + ₹{formatInr(latest.flight_return_price)}</dd>
                </div>
                <div>
                  <dt>Hotel</dt>
                  <dd>₹{formatInr(latest.hotel_total_price)}</dd>
                </div>
                <div>
                  <dt>Cabs</dt>
                  <dd>₹{formatInr(latest.cab_outbound_price)} + ₹{formatInr(latest.cab_return_price)}</dd>
                </div>
                <div className="total-row">
                  <dt>Total</dt>
                  <dd>
                    ₹{formatInr(latest.total_price)}
                    <span className={`status-tag status-${latest.status}`}>{latest.status}</span>
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="muted">No price checked yet for this simulated user.</p>
            )}

            <div className="card-actions">
              <button type="button" onClick={handleCheckPrice} disabled={panelBusy || requestId === null}>
                {panelBusy ? 'Working...' : 'Check price now'}
              </button>
              <button type="button" className="secondary-button" onClick={handleBookNow} disabled={panelBusy || requestId === null}>
                {panelBusy ? 'Working...' : 'Book now'}
              </button>
              {directory && (
                <button type="button" className="secondary-button" onClick={() => setShowBrowser((v) => !v)}>
                  {showBrowser ? 'Hide options' : 'Browse the specific options'}
                </button>
              )}
            </div>
            {panelMessage && <p className="muted">{panelMessage}</p>}

            {request && <PriceHistoryChart observations={observations} budget={Number(request.budget_inr)} />}

            {showBrowser && directory && <TripDirectoryBrowser directory={directory} />}
          </div>

          {raceStatus && raceStatus.entries.length > 0 && (
            <div className="card">
              <h2>Shared room race</h2>
              <p className="muted">{raceStatus.rooms_remaining} room(s) still unclaimed.</p>
              <ul className="lab-mini-list">
                {raceStatus.entries.map((e) => (
                  <li key={e.request_id}>
                    <span>
                      {labelFor(e.request_id)} · {e.origin} → {e.destination}
                    </span>
                    <span>
                      {e.hotel_status ? (
                        <span className={`status-tag status-${e.hotel_status}`}>{e.hotel_status}</span>
                      ) : (
                        <span className="muted">not booked yet</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {booking && (
            <div className="card">
              <h2>Booking attempt</h2>
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
                    It was actually booked
                  </button>
                  <button type="button" className="secondary-button" disabled={panelBusy} onClick={() => handleReconcile('failed')}>
                    It was never booked
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="card">
            <h2>Simulated notifications</h2>
            {simulatedNotifications.length === 0 ? (
              <p className="muted">None yet.</p>
            ) : (
              <ul className="lab-mini-list">
                {simulatedNotifications.slice(0, MAX_NOTIFICATION_ROWS).map((n) => (
                  <li key={n.id}>
                    <span>{n.origin} → {n.destination}: ₹{formatInr(n.total_price)}</span>
                    <span className="muted">
                      {n.reviewed_at ? 'reviewed' : 'new'}
                      {n.held_until ? ' · held' : ''}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card lab-log-card">
            <h2>Activity log</h2>
            {log.length === 0 ? (
              <p className="muted">Nothing logged yet.</p>
            ) : (
              <ul className="lab-log-list">
                {log.map((entry) => (
                  <li key={entry.id} className="lab-log-entry">
                    <div className="lab-log-entry-top">
                      <span className="lab-log-time">{new Date(entry.created_at).toLocaleTimeString()}</span>
                      <span className={statusBadgeClass(entry.status)}>{entry.status}</span>
                      {entry.duration_ms !== null && <span className="muted">{entry.duration_ms}ms</span>}
                    </div>
                    <p>{entry.summary}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <aside className="lab-timeline-panel">
          <h2>Timeline</h2>
          {timeline.length === 0 ? (
            <p className="muted">Nothing yet.</p>
          ) : (
            <ul className="timeline">
              {timeline
                .slice()
                .reverse()
                .map((event, i) => (
                  <li key={i} className={`timeline-event timeline-${event.type}`}>
                    <span className="muted">{new Date(event.at).toLocaleTimeString()}</span> - {event.summary}
                  </li>
                ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  );
}
