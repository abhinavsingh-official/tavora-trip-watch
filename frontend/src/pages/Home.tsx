import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';
import type { TripRequest, User } from '../types';

const AVATAR_EMOJI = ['🧑‍💼', '👩‍👩‍👧‍👦', '🧳'];

function ProfileCard({
  user,
  index,
  requests,
  onEnter,
}: {
  user: User;
  index: number;
  requests: TripRequest[];
  onEnter: () => void;
}) {
  /* skip cancelled requests, this is "what they're watching" not full history */
  const visibleRequests = requests.filter((r) => r.status !== 'cancelled');
  return (
    <div className="profile-card">
      <div className="profile-avatar">{AVATAR_EMOJI[index % AVATAR_EMOJI.length]}</div>
      <h2>{user.name}</h2>
      {visibleRequests.length === 0 ? (
        <p className="muted">No trip requests yet.</p>
      ) : (
        visibleRequests.map((r) => (
          <p key={r.id} className="muted">
            {r.origin} ⇄ {r.destination} · {r.adults} adult(s) · budget ₹{r.budget_inr}
          </p>
        ))
      )}
      <button onClick={onEnter}>View as {user.name}</button>
    </div>
  );
}

export default function Home() {
  const { users, setCurrentUserId } = useCurrentUser();
  const navigate = useNavigate();
  const [requestsByUser, setRequestsByUser] = useState<Record<number, TripRequest[]>>({});

  useEffect(() => {
    users.forEach((u) => {
      api
        .listRequests(u.id)
        .then((reqs) => setRequestsByUser((prev) => ({ ...prev, [u.id]: reqs })))
        .catch(() => {
          /* a preview failing to load isn't worth surfacing as a page error here */
        });
    });
  }, [users]);

  function enterAs(userId: number) {
    setCurrentUserId(userId);
    navigate('/dashboard');
  }

  return (
    <div className="page">
      <div className="hero">
        <h1>Trip Price Watch &amp; Booking</h1>
        <p className="page-intro">
          Watches flight, hotel, and cab prices for a trip over time, alerts the right
          traveller the moment a complete package meets their budget, and lets them review
          and confirm a simulated booking. Pick a traveller below to see their real requests
          and watch history.
        </p>
      </div>

      <div className="profile-grid">
        {users.map((u, i) => (
          <ProfileCard
            key={u.id}
            user={u}
            index={i}
            requests={requestsByUser[u.id] ?? []}
            onEnter={() => enterAs(u.id)}
          />
        ))}
      </div>
    </div>
  );
}
