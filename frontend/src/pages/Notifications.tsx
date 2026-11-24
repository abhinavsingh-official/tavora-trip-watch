import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { Notification } from '../types';

export default function Notifications() {
  const { currentUserId } = useCurrentUser();
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    if (currentUserId === null) return;
    api.listNotifications(currentUserId).then(setNotifications);
  }, [currentUserId]);

  return (
    <div className="page">
      <h1>Notifications</h1>
      <p className="page-intro">
        An alert here means a complete, fresh package crossed your budget - opening it re-checks
        the price and starts a 2-minute hold if you decide to book.
      </p>

      {notifications.length === 0 && (
        <p className="muted">
          No alerts yet - run "Check price now" on a request from the Dashboard until it
          crosses budget.
        </p>
      )}

      {notifications.map((n) => (
        <Link key={n.id} to={`/offer/${n.id}`} className="card card-link">
          <div className="card-header">
            <h2>
              {n.origin} ⇄ {n.destination}
              {!n.reviewed_at && <span className="status-tag status-pending">New</span>}
              <span className={`status-tag status-${n.quote_status}`}>{n.quote_status}</span>
            </h2>
            <span className="muted">
              Alerted {new Date(n.created_at).toLocaleString()}
              {n.reviewed_at && ` · last reviewed ${new Date(n.reviewed_at).toLocaleString()}`}
            </span>
          </div>
          <p>
            <strong>Itemized total at alert time: ₹{n.total_price ?? '-'}</strong>
          </p>
          <span className="muted">Open to review the current price →</span>
        </Link>
      ))}
    </div>
  );
}
