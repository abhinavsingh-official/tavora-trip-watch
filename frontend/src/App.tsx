import { NavLink, Route, Routes } from 'react-router-dom';
import { UserProvider, useCurrentUser } from './UserContext';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import RequestForm from './pages/RequestForm';
import Notifications from './pages/Notifications';
import OfferReview from './pages/OfferReview';
import BookingResult from './pages/BookingResult';
import TripStory from './pages/TripStory';
import Lab from './pages/Lab';
import Ops from './pages/Ops';

function UserSwitcher() {
  const { users, currentUserId, setCurrentUserId, loadError } = useCurrentUser();

  if (loadError) {
    return <span className="user-switcher error-text">Failed to load users: {loadError}</span>;
  }

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
            Home
          </NavLink>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/new">New request</NavLink>
          <NavLink to="/notifications">Notifications</NavLink>
          <NavLink to="/ops">Operations</NavLink>
          <NavLink to="/lab" className="lab-link">
            Scenario Lab
          </NavLink>
        </nav>
        <UserSwitcher />
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/new" element={<RequestForm />} />
          <Route path="/requests/:requestId/edit" element={<RequestForm />} />
          <Route path="/requests/:requestId/story" element={<TripStory />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/offer/:notificationId" element={<OfferReview />} />
          <Route path="/booking/:bookingId" element={<BookingResult />} />
          <Route path="/ops" element={<Ops />} />
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
