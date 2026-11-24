/* Mirrors backend/app/schemas.py - kept in sync by hand for V1 (no codegen yet). */

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
  /*
   * V7, audit finding #1: compared against a PriceObservation's own
   * observed_at to flag a displayed total as stale after an edit.
   */
  updated_at: string;
  /* True if this request has been edited/paused/cancelled away from its
   * original seed values - drives the "Return to default" button. */
  has_drifted_from_default: boolean;
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

/*
 * Every field optional - a PATCH only sends what actually changed. Status
 * isn't here on purpose - pause/cancel/reactivate are their own endpoints.
 */
export type TripRequestUpdate = Partial<Omit<TripRequestCreate, 'user_id'>>;

/* "complete" | "provisional" | "unavailable" - see backend/app/pricing.py */
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
  /*
   * V2: the real hold - null until reviewed, or if the last review came back
   * incomplete (nothing valid to hold).
   */
  held_observation_id: number | null;
  held_until: string | null;
  /*
   * V7, audit finding #5: lets the Notifications list show itinerary,
   * itemized total, and quote status per Sec. 07, instead of a bare,
   * indistinguishable "Request #N" repeated for every alert.
   */
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

/*
 * "fail" (V2) | "unavailable" (inventory disappeared) | "timeout" (supplier
 * response never resolves) - see backend/app/sim_controller.py.
 */
export type LabBookingOutcome = 'fail' | 'unavailable' | 'timeout';

/*
 * One row of the Scenario Lab's visible evidence trail - see
 * backend/app/models.py's SimulationLogEntry docstring.
 */
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
