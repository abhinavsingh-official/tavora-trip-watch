import { useCurrentUser } from '../UserContext';

const AVATAR_EMOJI = ['🧑‍💼', '👩‍👩‍👧‍👦', '🧳'];

/* Static filler so the sidebar reads like a real travel site, not just a
 * user switcher - not wired to anything real. */
const POPULAR_ROUTES = [
  { route: 'Mumbai → Goa', price: '₹6,200' },
  { route: 'Delhi → Manali', price: '₹5,800' },
  { route: 'Bengaluru → Gokarna', price: '₹3,900' },
];

const TRAVEL_TIP = 'Book 30+ days ahead for the widest range of fares and room types.';

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

      <div className="sidebar-widget">
        <h3>Popular routes</h3>
        <ul>
          {POPULAR_ROUTES.map((r) => (
            <li key={r.route}>
              <span>{r.route}</span>
              <span>{r.price}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="sidebar-widget">
        <h3>Travel tip</h3>
        <p className="sidebar-tip">{TRAVEL_TIP}</p>
      </div>
    </aside>
  );
}
