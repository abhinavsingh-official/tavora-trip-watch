import { Link, NavLink, Route, Routes } from 'react-router-dom';
import { UserProvider } from './UserContext';
import Sidebar from './components/Sidebar';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import RequestForm from './pages/RequestForm';
import Notifications from './pages/Notifications';
import OfferReview from './pages/OfferReview';
import BookingResult from './pages/BookingResult';
import TripStory from './pages/TripStory';
import Lab from './pages/Lab';
import Ops from './pages/Ops';

function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-title">
          Trip Price Watch
        </Link>
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
      </header>

      <div className="app-body">
        <Sidebar />
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
