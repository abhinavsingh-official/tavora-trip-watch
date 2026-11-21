import { NavLink, Route, Routes } from 'react-router-dom';
import { UserProvider, useCurrentUser } from './UserContext';
import Dashboard from './pages/Dashboard';
import RequestForm from './pages/RequestForm';
import Notifications from './pages/Notifications';
import OfferReview from './pages/OfferReview';
import BookingResult from './pages/BookingResult';
import Lab from './pages/Lab';

function UserSwitcher() {
  const { users, currentUserId, setCurrentUserId } = useCurrentUser();

  if (users.length === 0) {
    return <span className="user-switcher">Loading users...</span>;
  }

  return (
    <select
      className="user-switcher"
      value={currentUserId ?? ''}
      onChange={(e) => setCurrentUserId(Number(e.target.value))}
    >
      {users.map((u) => (
        <option key={u.id} value={u.id}>
          {u.name}
        </option>
      ))}
    </select>
  );
}

function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-title">Trip Price Watch</span>
        <nav className="app-nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/new">New request</NavLink>
          <NavLink to="/notifications">Notifications</NavLink>
          <NavLink to="/lab" className="lab-link">
            Scenario Lab
          </NavLink>
        </nav>
        <UserSwitcher />
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new" element={<RequestForm />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/offer/:notificationId" element={<OfferReview />} />
          <Route path="/booking/:bookingId" element={<BookingResult />} />
          <Route path="/lab" element={<Lab />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <UserProvider>
      <AppShell />
    </UserProvider>
  );
}
