import { useCurrentUser } from '../UserContext';

const AVATAR_EMOJI = ['🧑‍💼', '👩‍👩‍👧‍👦', '🧳'];

export default function Sidebar() {
  const { users, currentUserId, setCurrentUserId, loadError } = useCurrentUser();

  const currentIndex = users.findIndex((u) => u.id === currentUserId);
  const currentUser = currentIndex >= 0 ? users[currentIndex] : null;
  const avatar = AVATAR_EMOJI[Math.max(currentIndex, 0) % AVATAR_EMOJI.length];

  return (
    <aside className="sidebar">
      <div className="sidebar-user-card">
        <span className="sidebar-avatar">{avatar}</span>
        <div>
          <p className="sidebar-label">Viewing as</p>
          {loadError ? (
            <p className="error-text">Failed to load users</p>
          ) : currentUser ? (
            <p className="sidebar-name">{currentUser.name}</p>
          ) : (
            <p className="muted">Loading...</p>
          )}
        </div>
      </div>

      {users.length > 0 && (
        <select
          className="sidebar-switcher"
          value={currentUserId ?? ''}
          onChange={(e) => setCurrentUserId(Number(e.target.value))}
        >
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              Switch to {u.name}
            </option>
          ))}
        </select>
      )}
    </aside>
  );
}
