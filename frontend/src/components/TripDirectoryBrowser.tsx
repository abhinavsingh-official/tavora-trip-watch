import { useEffect, useState } from 'react';
import { formatInr } from '../format';
import type {
  CabDirectoryCandidate,
  FlightDirectoryCandidate,
  HotelDirectoryCandidate,
  TripDirectory,
} from '../types';

// Decorative only, not real amenity data - just enough variety that 40+ rows don't look like a database dump
const HOTEL_PERKS = ['Free Wi-Fi', 'Breakfast included', 'Free cancellation', 'Pool access', 'Late checkout'];
const FLIGHT_PERKS = ['Free meal', 'Extra legroom', 'Priority boarding', 'Window seat available'];
const CAB_PERKS = ['AC', 'Sanitised vehicle', 'English-speaking driver', 'Free waiting time'];

function perksFor(list: string[], seed: number, count: number): string[] {
  const out: string[] = [];
  for (let i = 0; i < count; i++) {
    out.push(list[(seed + i) % list.length]);
  }
  return out;
}

type SortOrder =
  | 'price-asc'
  | 'price-desc'
  | 'stars-desc'
  | 'stops-asc'
  | 'capacity-desc'
  | 'luggage-desc';

const SORT_LABELS: Record<SortOrder, string> = {
  'price-asc': 'Price: low to high',
  'price-desc': 'Price: high to low',
  'stars-desc': 'Star rating: high to low',
  'stops-asc': 'Fewest stops',
  'capacity-desc': 'Most seats',
  'luggage-desc': 'Most luggage space',
};

function SortToggle({ value, onChange, options }: { value: SortOrder; onChange: (v: SortOrder) => void; options: SortOrder[] }) {
  return (
    <div className="sort-toggle">
      <span className="muted">Sort by</span>
      <select value={value} onChange={(e) => onChange(e.target.value as SortOrder)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {SORT_LABELS[o]}
          </option>
        ))}
      </select>
    </div>
  );
}

const HOTEL_SORTS: SortOrder[] = ['price-asc', 'price-desc', 'stars-desc'];
const FLIGHT_SORTS: SortOrder[] = ['price-asc', 'price-desc', 'stops-asc'];
const CAB_SORTS: SortOrder[] = ['price-asc', 'price-desc', 'capacity-desc', 'luggage-desc'];

function HotelRow({ candidate, index, chosen, onChoose }: { candidate: HotelDirectoryCandidate; index: number; chosen: boolean; onChoose: () => void }) {
  return (
    <button type="button" className={`directory-row${chosen ? ' selected' : ''}`} onClick={onChoose}>
      <img src="/images/hotel.jpg" alt="" className="directory-row-image" />
      <div className="directory-row-body">
        <div className="directory-row-top">
          <span className="candidate-title">{candidate.hotel_name}</span>
          {candidate.selected && <span className="selected-badge">Cheapest found</span>}
        </div>
        <div className="candidate-detail">
          {candidate.category_name ?? `${candidate.star_rating}-star`}
          {candidate.room_description ? ` · ${candidate.room_description}` : ''}
        </div>
        <div className="perk-chips">
          {perksFor(HOTEL_PERKS, index, 2).map((p) => (
            <span key={p} className="perk-chip">{p}</span>
          ))}
        </div>
      </div>
      <div className="directory-row-price">₹{formatInr(candidate.price_inr)}</div>
    </button>
  );
}

function FlightRow({ candidate, index, chosen, onChoose }: { candidate: FlightDirectoryCandidate; index: number; chosen: boolean; onChoose: () => void }) {
  return (
    <button type="button" className={`directory-row${chosen ? ' selected' : ''}`} onClick={onChoose}>
      <img src="/images/flight.jpg" alt="" className="directory-row-image" />
      <div className="directory-row-body">
        <div className="directory-row-top">
          <span className="candidate-title">{candidate.carrier_name} {candidate.flight_number}</span>
          {candidate.selected && <span className="selected-badge">Cheapest found</span>}
        </div>
        <div className="candidate-detail">
          {candidate.departure_time} → {candidate.arrival_time} ·{' '}
          {candidate.stops === 0 ? 'Non-stop' : `${candidate.stops} stop(s)`}
        </div>
        <div className="perk-chips">
          {perksFor(FLIGHT_PERKS, index, 2).map((p) => (
            <span key={p} className="perk-chip">{p}</span>
          ))}
        </div>
      </div>
      <div className="directory-row-price">₹{formatInr(candidate.price_inr)}</div>
    </button>
  );
}

function CabRow({ candidate, index, chosen, onChoose }: { candidate: CabDirectoryCandidate; index: number; chosen: boolean; onChoose: () => void }) {
  return (
    <button type="button" className={`directory-row${chosen ? ' selected' : ''}`} onClick={onChoose}>
      <img src="/images/cab.jpg" alt="" className="directory-row-image" />
      <div className="directory-row-body">
        <div className="directory-row-top">
          <span className="candidate-title">{candidate.vendor_name} ({candidate.vehicle_class})</span>
          {candidate.selected && <span className="selected-badge">Cheapest found</span>}
        </div>
        <div className="candidate-detail">
          Up to {candidate.passenger_capacity} people · {candidate.luggage_capacity} bags · ~
          {candidate.distance_km} km transfer at ₹{formatInr(candidate.per_km_rate_inr)}/km
        </div>
        <div className="perk-chips">
          {perksFor(CAB_PERKS, index, 2).map((p) => (
            <span key={p} className="perk-chip">{p}</span>
          ))}
        </div>
      </div>
      <div className="directory-row-price">₹{formatInr(candidate.price_per_leg_inr)} one-way</div>
    </button>
  );
}

const PAGE_SIZE = 8;

// Shared hotel/flight/cab browsing tabs between "Your Bookings" and the Simulation page, to avoid two copies
export default function TripDirectoryBrowser({ directory }: { directory: TripDirectory }) {
  const [tab, setTab] = useState<'hotels' | 'flights' | 'cabs'>('hotels');
  const [sortOrder, setSortOrder] = useState<SortOrder>('price-asc');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [chosenHotel, setChosenHotel] = useState(0);
  const [chosenOutbound, setChosenOutbound] = useState(0);
  const [chosenReturn, setChosenReturn] = useState(0);
  const [chosenCab, setChosenCab] = useState(0);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [tab, sortOrder]);

  useEffect(() => {
    setSortOrder('price-asc');
  }, [tab]);

  function sorted<T extends {
    price_inr?: number; price_per_leg_inr?: number; star_rating?: number;
    stops?: number; passenger_capacity?: number; luggage_capacity?: number;
  }>(list: T[]): T[] {
    const price = (c: T) => c.price_inr ?? c.price_per_leg_inr ?? 0;
    const copy = [...list];
    copy.sort((a, b) => {
      switch (sortOrder) {
        case 'price-desc':
          return price(b) - price(a);
        case 'stars-desc':
          return (b.star_rating ?? 0) - (a.star_rating ?? 0) || price(a) - price(b);
        case 'stops-asc':
          return (a.stops ?? 0) - (b.stops ?? 0) || price(a) - price(b);
        case 'capacity-desc':
          return (b.passenger_capacity ?? 0) - (a.passenger_capacity ?? 0) || price(a) - price(b);
        case 'luggage-desc':
          return (b.luggage_capacity ?? 0) - (a.luggage_capacity ?? 0) || price(a) - price(b);
        case 'price-asc':
        default:
          return price(a) - price(b);
      }
    });
    return copy;
  }

  return (
    <div className="trip-directory-browser">
      <div className="booking-steps">
        <button type="button" className={`booking-step${tab === 'hotels' ? ' active' : ''}`} onClick={() => setTab('hotels')}>
          <span className="booking-step-icon">🏨</span> Hotels
        </button>
        <button type="button" className={`booking-step${tab === 'flights' ? ' active' : ''}`} onClick={() => setTab('flights')}>
          <span className="booking-step-icon">✈️</span> Flights
        </button>
        <button type="button" className={`booking-step${tab === 'cabs' ? ' active' : ''}`} onClick={() => setTab('cabs')}>
          <span className="booking-step-icon">🚕</span> Cabs
        </button>
      </div>

      {tab === 'hotels' && (
        <div className="story-section">
          <div className="directory-section-header">
            <h3>Hotels</h3>
            <SortToggle value={sortOrder} onChange={setSortOrder} options={HOTEL_SORTS} />
          </div>
          {directory.hotel_candidates.length === 0 ? (
            <p className="muted">No real hotel options available for this request right now.</p>
          ) : (
            <>
              <div className="directory-list">
                {sorted(directory.hotel_candidates).slice(0, visibleCount).map((c, i) => (
                  <HotelRow key={i} candidate={c} index={i} chosen={i === chosenHotel} onChoose={() => setChosenHotel(i)} />
                ))}
              </div>
              {visibleCount < directory.hotel_candidates.length && (
                <button className="secondary-button" onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}>
                  Show more ({directory.hotel_candidates.length - visibleCount} left)
                </button>
              )}
            </>
          )}
        </div>
      )}

      {tab === 'flights' && (
        <>
          <div className="story-section">
            <div className="directory-section-header">
              <h3>Outbound flight</h3>
              <SortToggle value={sortOrder} onChange={setSortOrder} options={FLIGHT_SORTS} />
            </div>
            <div className="directory-list">
              {sorted(directory.outbound_flight_candidates).slice(0, visibleCount).map((c, i) => (
                <FlightRow key={i} candidate={c} index={i} chosen={i === chosenOutbound} onChoose={() => setChosenOutbound(i)} />
              ))}
            </div>
          </div>
          <div className="story-section">
            <h3>Return flight</h3>
            <div className="directory-list">
              {sorted(directory.return_flight_candidates).slice(0, visibleCount).map((c, i) => (
                <FlightRow key={i} candidate={c} index={i} chosen={i === chosenReturn} onChoose={() => setChosenReturn(i)} />
              ))}
            </div>
            {visibleCount < Math.max(directory.outbound_flight_candidates.length, directory.return_flight_candidates.length) && (
              <button className="secondary-button" onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}>
                Show more
              </button>
            )}
          </div>
        </>
      )}

      {tab === 'cabs' && (
        <div className="story-section">
          <div className="directory-section-header">
            <h3>Airport transfers</h3>
            <SortToggle value={sortOrder} onChange={setSortOrder} options={CAB_SORTS} />
          </div>
          <p className="simulated-banner">
            Simulated - no real cab supplier API exists for this category. Each price is a real
            per-km market rate for that vehicle class times an assumed ~30 km airport transfer,
            not an arbitrary flat number.
          </p>
          <div className="directory-list">
            {sorted(directory.cab_candidates).map((c, i) => (
              <CabRow key={i} candidate={c} index={i} chosen={i === chosenCab} onChoose={() => setChosenCab(i)} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
