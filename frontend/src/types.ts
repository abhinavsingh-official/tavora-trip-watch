// Mirrors backend/app/schemas.py - kept in sync by hand for V1 (no codegen yet).

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

// Every field optional - a PATCH only sends what actually changed. Status
// isn't here on purpose - pause/cancel/reactivate are their own endpoints.
export type TripRequestUpdate = Partial<Omit<TripRequestCreate, 'user_id'>>;

// "complete" | "provisional" | "unavailable" - see backend/app/pricing.py
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
  // V2: the real hold - null until reviewed, or if the last review came back
  // incomplete (nothing valid to hold).
  held_observation_id: number | null;
  held_until: string | null;
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

export interface TimelineEvent {
  type: 'observation' | 'notification' | 'booking';
  at: string;
  summary: string;
}
