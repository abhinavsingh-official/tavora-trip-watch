import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { TripRequest } from '../types';

export default function TrashBin() {
  const { currentUserId } = useCurrentUser();
  const [cancelled, setCancelled] = useState<TripRequest[]>([]);
  const [open, setOpen] = useState(false);
  const [restoringId, setRestoringId] = useState<number | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  function load() {
    if (currentUserId === null) return;
    api
      .listRequests(currentUserId)
      .then((all) => setCancelled(all.filter((r) => r.status === 'cancelled')))
      .catch(() => {});
  }

  useEffect(load, [currentUserId]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  async function handleRestore(requestId: number) {
    if (currentUserId === null) return;
    setRestoringId(requestId);
    try {
      await api.reactivateRequest(requestId, currentUserId);
      load();
    } finally {
      setRestoringId(null);
    }
  }

  return (
    <div className="trash-bin" ref={wrapRef}>
      <button
        type="button"
        className="icon-nav-button"
        onClick={() => setOpen((o) => !o)}
        aria-label="Trash"
        title="Cancelled requests"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 6h18" strokeLinecap="round" />
          <path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" strokeLinecap="round" />
          <path d="M19 6l-1 14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1L5 6" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M10 11v6M14 11v6" strokeLinecap="round" />
        </svg>
        {cancelled.length > 0 && <span className="bell-badge">{cancelled.length}</span>}
      </button>

      {open && (
        <div className="bell-dropdown">
          <div className="bell-dropdown-header">Trash</div>
          {cancelled.length === 0 ? (
            <p className="muted bell-empty">Nothing cancelled right now.</p>
          ) : (
            <ul className="bell-list trash-list">
              {cancelled.map((r) => (
                <li key={r.id}>
                  <span>
                    {r.origin} ⇄ {r.destination}
                  </span>
                  <button
                    className="secondary-button"
                    disabled={restoringId === r.id}
                    onClick={() => handleRestore(r.id)}
                  >
                    {restoringId === r.id ? 'Restoring...' : 'Restore'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
