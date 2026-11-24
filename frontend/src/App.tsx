import { Link, NavLink, Route, Routes } from 'react-router-dom';
import { UserProvider } from './UserContext';
import Sidebar from './components/Sidebar';
import NotificationBell from './components/NotificationBell';
import TrashBin from './components/TrashBin';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import RequestForm from './pages/RequestForm';
import OfferReview from './pages/OfferReview';
import BookingResult from './pages/BookingResult';
import YourBookings from './pages/YourBookings';
import Lab from './pages/Lab';

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
          <NavLink to="/lab" className="lab-link">
            Simulation
          </NavLink>
          <TrashBin />
          <NotificationBell />
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
            <Route path="/requests/:requestId/story" element={<YourBookings />} />
            <Route path="/offer/:notificationId" element={<OfferReview />} />
            <Route path="/booking/:bookingId" element={<BookingResult />} />
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
