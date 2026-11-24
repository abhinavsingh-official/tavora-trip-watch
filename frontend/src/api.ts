/* Only file that talks to the backend directly - pages go through api, not fetch(). */

import type {
  BookingAttempt,
  LabBookingOutcome,
  LabClock,
  LabComponent,
  LabMutatePricesResult,
  LabTriggerCycleResult,
  Notification,
  NotificationReview,
  PriceObservation,
  SimulationLogEntryOut,
  TimelineEvent,
  TripDirectory,
  TripRequest,
  TripRequestCreate,
  TripRequestUpdate,
  TripStory,
  User,
} from './types';

/*
 * Empty by default, so calls go to relative "/api/..." paths - works in dev via
 * the vite proxy, or in prod if frontend and backend share an origin. For a
 * split deploy, set VITE_API_BASE_URL to the backend's real URL at build time.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

/*
 * Turns the raw error body into something readable instead of
 * `400 Bad Request: {"detail":"..."}`. FastAPI validation errors (422) come
 * back as an array of {msg} objects rather than a plain string, so that case
 * gets handled separately.
 */
function _extractMessage(body: string, status: number, statusText: string): string {
  try {
    const parsed = JSON.parse(body);
    const detail = parsed?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d) => d?.msg ?? JSON.stringify(d)).join('; ');
    }
  } catch {
    /* not JSON, fall through to raw body */
  }
  return body || `${status} ${statusText}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(_extractMessage(body, response.status, response.statusText));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

export const api = {
  listUsers: () => request<User[]>('/users'),

  createRequest: (payload: TripRequestCreate) =>
    request<TripRequest>('/requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listRequests: (userId: number) =>
    request<TripRequest[]>(`/requests?user_id=${userId}`),

  getRequest: (requestId: number, userId: number) =>
    request<TripRequest>(`/requests/${requestId}?user_id=${userId}`),

  updateRequest: (requestId: number, userId: number, payload: TripRequestUpdate) =>
    request<TripRequest>(`/requests/${requestId}?user_id=${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  pauseRequest: (requestId: number, userId: number) =>
    request<TripRequest>(`/requests/${requestId}/pause?user_id=${userId}`, { method: 'POST' }),

  cancelRequest: (requestId: number, userId: number) =>
    request<TripRequest>(`/requests/${requestId}/cancel?user_id=${userId}`, { method: 'POST' }),

  reactivateRequest: (requestId: number, userId: number) =>
    request<TripRequest>(`/requests/${requestId}/reactivate?user_id=${userId}`, {
      method: 'POST',
    }),

  resetRequestToDefault: (requestId: number, userId: number) =>
    request<TripRequest>(`/requests/${requestId}/reset-to-default?user_id=${userId}`, {
      method: 'POST',
    }),

  listObservations: (requestId: number, userId: number) =>
    request<PriceObservation[]>(`/requests/${requestId}/observations?user_id=${userId}`),

  checkPrice: (requestId: number, userId: number) =>
    request<PriceObservation>(`/requests/${requestId}/check?user_id=${userId}`, {
      method: 'POST',
    }),

  listNotifications: (userId: number) =>
    request<Notification[]>(`/notifications?user_id=${userId}`),

  reviewNotification: (notificationId: number, userId: number) =>
    request<NotificationReview>(`/notifications/${notificationId}/review?user_id=${userId}`, {
      method: 'POST',
    }),

  /* server derives the total from the held observation, nothing to send here */
  book: (requestId: number, notificationId: number, userId: number) =>
    request<BookingAttempt>(`/requests/${requestId}/book?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ notification_id: notificationId }),
    }),

  /* Books the current best price right now - no notification to click first. */
  buyNow: (requestId: number, userId: number) =>
    request<BookingAttempt>(`/requests/${requestId}/buy-now?user_id=${userId}`, {
      method: 'POST',
    }),

  getBooking: (bookingId: number, userId: number) =>
    request<BookingAttempt>(`/bookings/${bookingId}?user_id=${userId}`),

  reconcileBooking: (bookingId: number, userId: number, outcome: 'confirmed' | 'failed') =>
    request<BookingAttempt>(`/bookings/${bookingId}/reconcile?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ outcome }),
    }),

  labClock: () => request<LabClock>('/lab/clock'),

  labAdvanceClock: (minutes: number) =>
    request<LabClock>('/lab/clock/advance', {
      method: 'POST',
      body: JSON.stringify({ minutes }),
    }),

  labOverride: (requestId: number, component: LabComponent, price: number) =>
    request<{ ok: boolean }>('/lab/override', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, component, price }),
    }),

  labFailComponent: (requestId: number, component: LabComponent, outcome: LabBookingOutcome = 'fail') =>
    request<{ ok: boolean }>('/lab/fail-component', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, component, outcome }),
    }),

  labCancelFailure: (requestId: number, component: LabComponent) =>
    request<{ ok: boolean }>('/lab/cancel-failure', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, component }),
    }),

  labRestartAfter: (requestId: number, component: LabComponent) =>
    request<{ ok: boolean }>('/lab/restart-after', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, component }),
    }),

  labTriggerCycle: () =>
    request<LabTriggerCycleResult>('/lab/trigger-cycle', { method: 'POST' }),

  labReset: () => request<{ ok: boolean }>('/lab/reset', { method: 'POST' }),

  labMutatePrices: () => request<LabMutatePricesResult>('/lab/mutate-prices', { method: 'POST' }),

  labBookNow: (requestId: number) =>
    request<BookingAttempt>('/lab/book-now', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId }),
    }),

  /* Shocks this one trip's market by an exact signed fraction and checks
     the price in the same call - the Simulation page's shock slider. */
  labShockAndCheck: (requestId: number, shockFraction: number) =>
    request<PriceObservation>('/lab/shock-and-check', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, shock_fraction: shockFraction }),
    }),

  labLog: (limit = 100) => request<SimulationLogEntryOut[]>(`/lab/log?limit=${limit}`),

  labLogClear: () => request<{ ok: boolean; cleared: number }>('/lab/log/clear', { method: 'POST' }),

  labSharedRoomScenario: (requestIds: number[], roomsRemaining: number) =>
    request<{ ok: boolean }>('/lab/shared-room-scenario', {
      method: 'POST',
      body: JSON.stringify({ request_ids: requestIds, rooms_remaining: roomsRemaining }),
    }),

  listPartialBookings: (userId: number) =>
    request<BookingAttempt[]>(`/ops/partial-bookings?user_id=${userId}`),

  getRequestTimeline: (requestId: number, userId: number) =>
    request<TimelineEvent[]>(`/ops/requests/${requestId}/timeline?user_id=${userId}`),

  getTripStory: (requestId: number, userId: number) =>
    request<TripStory>(`/requests/${requestId}/story?user_id=${userId}`),

  getTripDirectory: (requestId: number, userId: number) =>
    request<TripDirectory>(`/requests/${requestId}/directory?user_id=${userId}`),
};
