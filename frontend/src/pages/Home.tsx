import { Link } from 'react-router-dom';

const STEPS = [
  { title: 'Tell us your trip', detail: 'Route, dates, travellers, and a budget.' },
  { title: 'We watch prices', detail: 'Flights, hotels, and cabs, checked every 5 minutes.' },
  { title: 'You book when it is right', detail: 'An alert fires the moment a package meets budget.' },
];

export default function Home() {
  return (
    <div className="page">
      <div className="hero">
        <img src="/images/destination.jpg" alt="" className="home-hero-image" />
        <h1>Trip Price Watch &amp; Booking</h1>
        <p className="page-intro">
          Watch flight, hotel, and cab prices for a trip, and book the moment a complete package
          meets your budget.
        </p>
        <div className="hero-actions">
          <Link to="/new" className="button-link">
            Start a new watch
          </Link>
          <Link to="/dashboard" className="button-link secondary-button">
            Go to dashboard
          </Link>
        </div>
      </div>

      <div className="card">
        <h2>How it works</h2>
        <ol className="home-steps">
          {STEPS.map((s) => (
            <li key={s.title}>
              <strong>{s.title}</strong>
              <span className="muted">{s.detail}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
