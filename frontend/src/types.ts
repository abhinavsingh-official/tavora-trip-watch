/* Mirrors backend/app/schemas.py - kept in sync by hand, no codegen. */

export interface User {
  id: number;
  name: string;
}

export interface TripRequest {
  id: number;
  user_id: number;
  origin: string;
  destination: string;
  outbound_date: string;
  return_date: string;
  adults: number;
  rooms: number;
  budget_inr: number;
  max_stops_outbound: number;
  max_stops_return: number;
  min_star_rating: number;
  checked_baggage: boolean;
  status: string;
  updated_at: string; // compared against the observation's observed_at to flag a stale total
  has_drifted_from_default: boolean; // true if edited/paused/cancelled away from seed values
}

export interface TripRequestCreate {
  user_id: number;
  origin: string;
  destination: string;
  outbound_date: string;
  return_date: string;
  adults: number;
  rooms: number;
  budget_inr: number;
  max_stops_outbound: number;
  max_stops_return: number;
  min_star_rating: number;
  checked_baggage: boolean;
}

/* Everything optional since a PATCH only sends what changed. Status has its own endpoints (pause/cancel/reactivate), not included here. */
export type TripRequestUpdate = Partial<Omit<TripRequestCreate, 'user_id'>>;

/* see backend/app/pricing.py for what each status means */
export type ComponentStatus = 'complete' | 'provisional' | 'unavailable';

export interface PriceObservation {
  id: number;
  request_id: number;
  observed_at: string;
  flight_outbound_price: number | null;
  flight_return_price: number | null;
  flight_status: ComponentStatus;
  hotel_total_price: number | null;
  hotel_status: ComponentStatus;
  cab_outbound_price: number | null;
  cab_return_price: number | null;
  cab_status: ComponentStatus;
  taxes_fees: number | null;
  total_price: number | null;
  status: ComponentStatus;
}

export interface Notification {
  id: number;
  request_id: number;
  observation_id: number;
  created_at: string;
  reviewed_at: string | null;
  /* null until reviewed, or if the last review had nothing valid to hold */
  held_observation_id: number | null;
  held_until: string | null;
  /* lets the notifications list show itinerary + total instead of just "Request #N" */
  origin: string;
  destination: string;
  total_price: number | null;
  quote_status: string;
}

export interface NotificationReview {
  notification: Notification;
  original_observation: PriceObservation;
  current_observation: PriceObservation;
}

export interface BookingAttempt {
  id: number;
  request_id: number;
  notification_id: number;
  created_at: string;
  accepted_total: number;
  flight_status: string;
  hotel_status: string;
  cab_status: string;
  aggregate_status: string;
  supplier_ref_flight: string | null;
  supplier_ref_hotel: string | null;
  supplier_ref_cab: string | null;
}

export interface LabClock {
  now: string;
}

export interface LabTriggerCycleResult {
  checked_request_ids: number[];
}

export type LabComponent = 'flight' | 'hotel' | 'cab';

/* fail | inventory disappeared | supplier never responds - see backend/app/sim_controller.py */
export type LabBookingOutcome = 'fail' | 'unavailable' | 'timeout';

/* one row of the Simulation's log - see SimulationLogEntry in backend/app/models.py */
export interface SimulationLogEntryOut {
  id: number;
  created_at: string;
  user_name: string | null;
  route_label: string | null;
  event_type: string;
  summary: string;
  flight_name: string | null;
  hotel_name: string | null;
  cab_name: string | null;
  total_cost_inr: number | null;
  is_simulated: boolean;
  status: 'finished' | 'failed' | 'unfinished' | 'info';
  duration_ms: number | null;
}

export interface LabMutatePricesResult {
  ok: boolean;
  flights_mutated: number;
  cabs_mutated: number;
  hotels_mutated: number;
}

export interface TimelineEvent {
  type: 'observation' | 'notification' | 'booking';
  at: string;
  summary: string;
}

export interface FlightCandidate {
  carrier_code: string | null;
  flight_number: number | null;
  departure_airport: string | null;
  arrival_airport: string | null;
  departure_time: string | null;
  arrival_time: string | null;
  stops: number;
  price_inr: number;
  selected: boolean;
}

export interface HotelCandidate {
  name: string | null;
  category_name: string | null;
  stars: number;
  price_inr: number;
  selected: boolean;
}

export interface CabQuote {
  outbound_price: number | null;
  return_price: number | null;
  status: string;
}

export interface TripStory {
  observation_id: number;
  observed_at: string;
  outbound_flight_candidates: FlightCandidate[];
  return_flight_candidates: FlightCandidate[];
  hotel_candidates: HotelCandidate[];
  cab: CabQuote;
}

export interface FlightDirectoryCandidate {
  carrier_code: string;
  carrier_name: string;
  flight_number: number;
  departure_time: string;
  arrival_time: string;
  stops: number;
  price_inr: number;
  selected: boolean;
}

export interface HotelDirectoryCandidate {
  hotel_name: string;
  category_name: string | null;
  star_rating: number;
  room_description: string | null;
  price_inr: number;
  selected: boolean;
}

export interface CabDirectoryCandidate {
  vendor_name: string;
  vehicle_class: string;
  passenger_capacity: number;
  luggage_capacity: number;
  distance_km: number;
  per_km_rate_inr: number;
  price_per_leg_inr: number;
  selected: boolean;
}

// The live candidate directory behind "Your Bookings" - always current, not a snapshot of one past check
export interface TripDirectory {
  outbound_flight_candidates: FlightDirectoryCandidate[];
  return_flight_candidates: FlightDirectoryCandidate[];
  hotel_candidates: HotelDirectoryCandidate[];
  cab_candidates: CabDirectoryCandidate[];
}

export interface SharedRoomRaceEntry {
  request_id: number;
  origin: string;
  destination: string;
  hotel_status: string | null;
  aggregate_status: string | null;
}

export interface SharedRoomStatus {
  rooms_remaining: number;
  entries: SharedRoomRaceEntry[];
}
