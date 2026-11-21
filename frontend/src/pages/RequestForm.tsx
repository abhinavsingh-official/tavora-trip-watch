import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { useCurrentUser } from '../UserContext';

const DEFAULT_OUTBOUND = '2026-12-26';
const DEFAULT_RETURN = '2026-12-29';

export default function RequestForm() {
  const { currentUserId } = useCurrentUser();
  const navigate = useNavigate();
  const { requestId } = useParams(); // present only on the edit route
  const isEditing = requestId !== undefined;

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
  const [loading, setLoading] = useState(isEditing);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isEditing || currentUserId === null) return;
    api
      .getRequest(Number(requestId), currentUserId)
      .then((r) => {
        setOrigin(r.origin);
        setDestination(r.destination);
        setOutboundDate(r.outbound_date);
        setReturnDate(r.return_date);
        setAdults(r.adults);
        setRooms(r.rooms);
        setBudgetInr(r.budget_inr);
        setMaxStopsOutbound(r.max_stops_outbound);
        setMaxStopsReturn(r.max_stops_return);
        setMinStarRating(r.min_star_rating);
        setCheckedBaggage(r.checked_baggage);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load request'))
      .finally(() => setLoading(false));
  }, [isEditing, requestId, currentUserId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (currentUserId === null) return;

    setSubmitting(true);
    setError(null);
    const payload = {
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
    };
    try {
      if (isEditing) {
        // Editing invalidates any stale held offer on this request (Sec. 03)
        // - handled entirely server-side, nothing extra needed here.
        await api.updateRequest(Number(requestId), currentUserId, payload);
      } else {
        await api.createRequest({ user_id: currentUserId, ...payload });
      }
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save request');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p className="muted">Loading...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>{isEditing ? 'Edit trip request' : 'New trip request'}</h1>
      {isEditing && (
        <p className="price-change-note">
          Saving changes will invalidate any held offer on this request - review it again
          afterward to get a current, bookable price.
        </p>
      )}
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
          {submitting ? 'Saving...' : isEditing ? 'Save changes' : 'Create request'}
        </button>
      </form>
    </div>
  );
}
