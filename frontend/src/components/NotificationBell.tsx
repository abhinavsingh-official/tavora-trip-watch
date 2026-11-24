import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { formatInr } from '../format';
import { useCurrentUser } from '../UserContext';
import type { Notification } from '../types';

const POLL_MS = 30_000;

export default function NotificationBell() {
  const { currentUserId } = useCurrentUser();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (currentUserId === null) return;
    let cancelled = false;
    function load() {
      api
        .listNotifications(currentUserId as number)
        .then((n) => !cancelled && setNotifications(n))
        .catch(() => {});
    }
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [currentUserId]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.reviewed_at).length;
  const recent = notifications.slice(0, 6);

  return (
    <div className="notification-bell" ref={wrapRef}>
      <button
        type="button"
        className="icon-nav-button"
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        title="Alerts"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
          <path
            d="M6 10a6 6 0 1 1 12 0c0 3.2 1 5 1.5 6H4.5C5 15 6 13.2 6 10Z"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M10 19a2 2 0 0 0 4 0" strokeLinecap="round" />
        </svg>
        {unreadCount > 0 && <span className="bell-badge">{unreadCount}</span>}
      </button>

      {open && (
        <div className="bell-dropdown">
          <div className="bell-dropdown-header">Alerts</div>
          {recent.length === 0 ? (
            <p className="muted bell-empty">No alerts yet.</p>
          ) : (
            <ul className="bell-list">
              {recent.map((n) => (
                <li key={n.id}>
                  <Link to={`/offer/${n.id}`} onClick={() => setOpen(false)}>
                    <span>
                      {n.origin} ⇄ {n.destination}
                      {!n.reviewed_at && <span className="status-tag status-pending">New</span>}
                    </span>
                    <span className="muted">₹{formatInr(n.total_price)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
