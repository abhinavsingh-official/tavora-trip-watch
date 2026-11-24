import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { TripRequest } from '../types';

export default function Home() {
  const { currentUserId, users } = useCurrentUser();
  const [requests, setRequests] = useState<TripRequest[]>([]);

  useEffect(() => {
    if (currentUserId === null) return;
    api.listRequests(currentUserId).then(setRequests).catch(() => setRequests([]));
  }, [currentUserId]);

  const currentUser = users.find((u) => u.id === currentUserId);
  const activeRequests = requests.filter((r) => r.status === 'active');

  return (
    <div className="page">
      <div className="hero">
        <img src="/images/destination.jpg" alt="" className="home-hero-image" />
        <h1>Trip Price Watch &amp; Booking</h1>
        <p className="page-intro">
          Watches flight, hotel, and cab prices for a trip and alerts you the moment a complete
          package meets your budget. Switch travellers from the sidebar any time.
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>{currentUser ? `${currentUser.name}'s watches` : 'Your watches'}</h2>
          <Link to="/new" className="button-link">
            + New request
          </Link>
        </div>
        {activeRequests.length === 0 ? (
          <p className="muted">No active requests yet - start one to begin watching prices.</p>
        ) : (
          <ul className="home-watch-list">
            {activeRequests.map((r) => (
              <li key={r.id}>
                <span>
                  {r.origin} ⇄ {r.destination}
                </span>
                <span className="muted">budget ₹{r.budget_inr}</span>
              </li>
            ))}
          </ul>
        )}
        <Link to="/dashboard" className="button-link secondary-button">
          Open dashboard
        </Link>
      </div>
    </div>
  );
}
