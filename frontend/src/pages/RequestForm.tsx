import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';

const DEFAULT_OUTBOUND = '2026-12-26';
const DEFAULT_RETURN = '2026-12-29';

export default function RequestForm() {
  const { currentUserId } = useCurrentUser();
  const navigate = useNavigate();

  const [origin, setOrigin] = useState('Mumbai');
  const [destination, setDestination] = useState('Goa');
  const [outboundDate, setOutboundDate] = useState(DEFAULT_OUTBOUND);
  const [returnDate, setReturnDate] = useState(DEFAULT_RETURN);
  const [adults, setAdults] = useState(2);
  const [rooms, setRooms] = useState(1);
  const [budgetInr, setBudgetInr] = useState(35000);
  const [maxStopsOutbound, setMaxStopsOutbound] = useState(2);
  const [maxStopsReturn, setMaxStopsReturn] = useState(2);
  const [minStarRating, setMinStarRating] = useState(0);
  const [checkedBaggage, setCheckedBaggage] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (currentUserId === null) return;

    setSubmitting(true);
    setError(null);
    try {
      await api.createRequest({
        user_id: currentUserId,
        origin,
        destination,
        outbound_date: outboundDate,
        return_date: returnDate,
        adults,
        rooms,
        budget_inr: budgetInr,
        max_stops_outbound: maxStopsOutbound,
        max_stops_return: maxStopsReturn,
        min_star_rating: minStarRating,
        checked_baggage: checkedBaggage,
      });
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create request');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <h1>New trip request</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label>
          Origin
          <input value={origin} onChange={(e) => setOrigin(e.target.value)} required />
        </label>
        <label>
          Destination
          <input
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            required
          />
        </label>
        <label>
          Outbound date
          <input
            type="date"
            value={outboundDate}
            onChange={(e) => setOutboundDate(e.target.value)}
            required
          />
        </label>
        <label>
          Return date
          <input
            type="date"
            value={returnDate}
            onChange={(e) => setReturnDate(e.target.value)}
            required
          />
        </label>
        <label>
          Adults
          <input
            type="number"
            min={1}
            value={adults}
            onChange={(e) => setAdults(Number(e.target.value))}
            required
          />
        </label>
        <label>
          Rooms
          <input
            type="number"
            min={1}
            value={rooms}
            onChange={(e) => setRooms(Number(e.target.value))}
            required
          />
        </label>
        <label>
          Budget (INR)
          <input
            type="number"
            min={0}
            value={budgetInr}
            onChange={(e) => setBudgetInr(Number(e.target.value))}
            required
          />
        </label>
        <label>
          Max stops (outbound)
          <input
            type="number"
            min={0}
            value={maxStopsOutbound}
            onChange={(e) => setMaxStopsOutbound(Number(e.target.value))}
          />
        </label>
        <label>
          Max stops (return)
          <input
            type="number"
            min={0}
            value={maxStopsReturn}
            onChange={(e) => setMaxStopsReturn(Number(e.target.value))}
          />
        </label>
        <label>
          Minimum star rating
          <input
            type="number"
            min={0}
            max={5}
            value={minStarRating}
            onChange={(e) => setMinStarRating(Number(e.target.value))}
          />
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={checkedBaggage}
            onChange={(e) => setCheckedBaggage(e.target.checked)}
          />
          Checked baggage required
        </label>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" disabled={submitting || currentUserId === null}>
          {submitting ? 'Creating...' : 'Create request'}
        </button>
      </form>
    </div>
  );
}
