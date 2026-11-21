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

export type LabComponent = 'flight' | 'hotel' | 'cab';
