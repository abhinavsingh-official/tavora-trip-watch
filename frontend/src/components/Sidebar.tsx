import { useLocation } from 'react-router-dom';
import { useCurrentUser } from '../UserContext';
import LabSidebarControls from './LabSidebarControls';

const AVATAR_EMOJI = ['🧑‍💼', '👩‍👩‍👧‍👦', '🧳'];

export default function Sidebar() {
  const location = useLocation();
  const isLab = location.pathname === '/lab';
  const { users, currentUserId, setCurrentUserId, loadError } = useCurrentUser();

  /* The Scenario user lives entirely inside the Simulation page now - it
     never needs to be "viewed as" from here, and keeping it out of this
     switcher is what actually keeps real and simulated activity separate. */
  const switchableUsers = users.filter((u) => u.name !== 'Scenario');

  const currentIndex = users.findIndex((u) => u.id === currentUserId);
  const currentUser = currentIndex >= 0 ? users[currentIndex] : null;
  const avatar = AVATAR_EMOJI[Math.max(currentIndex, 0) % AVATAR_EMOJI.length];

  return (
    <aside className="sidebar">
      <div className="sidebar-user-card">
        <span className="sidebar-avatar">{isLab ? '🧪' : avatar}</span>
        <div>
          <p className="sidebar-label">Viewing as</p>
          {/* Whichever real person is "selected" up top never actually
              applies inside the Simulation page - Lab.tsx always acts as
              the Scenario user, never currentUserId. Showing their name
              here while on /lab implied switching it would change
              something in the simulation; it never did. */}
          {isLab ? (
            <p className="sidebar-name">Simulation</p>
          ) : loadError ? (
            <p className="error-text">Failed to load users</p>
          ) : currentUser ? (
            <p className="sidebar-name">{currentUser.name}</p>
          ) : (
            <p className="muted">Loading...</p>
          )}
        </div>
      </div>

      {!isLab && switchableUsers.length > 0 && (
        <select
          className="sidebar-switcher"
          value={currentUserId ?? ''}
          onChange={(e) => setCurrentUserId(Number(e.target.value))}
        >
          {switchableUsers.map((u) => (
            <option key={u.id} value={u.id}>
              Switch to {u.name}
            </option>
          ))}
        </select>
      )}

      {isLab && <LabSidebarControls />}
    </aside>
  );
}
