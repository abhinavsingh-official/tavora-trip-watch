// The only file that knows the backend's URLs. Every page goes through here,
// never calls fetch() directly - see docs/versions/V1_MODULES.md.

import type {
  BookingAttempt,
  LabClock,
  LabComponent,
  LabTriggerCycleResult,
  Notification,
  NotificationReview,
  PriceObservation,
  TimelineEvent,
  TripRequest,
  TripRequestCreate,
  TripRequestUpdate,
  User,
} from './types';

// Empty by default - relative "/api/..." calls, which only resolve correctly
// in dev (via vite.config.ts's proxy) or when the frontend and backend are
// deployed to the same origin. For a split deploy, set VITE_API_BASE_URL to
// the backend's real URL (e.g. https://tavora-api.onrender.com) at build time.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
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

  // V2: the server derives the authoritative total from the held
  // observation itself - no accepted_total to send anymore.
  book: (requestId: number, notificationId: number, userId: number) =>
    request<BookingAttempt>(`/requests/${requestId}/book?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ notification_id: notificationId }),
    }),

  getBooking: (bookingId: number, userId: number) =>
    request<BookingAttempt>(`/bookings/${bookingId}?user_id=${userId}`),

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

  labFailComponent: (requestId: number, component: LabComponent) =>
    request<{ ok: boolean }>('/lab/fail-component', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, component }),
    }),

  labTriggerCycle: () =>
    request<LabTriggerCycleResult>('/lab/trigger-cycle', { method: 'POST' }),

  labReset: () => request<{ ok: boolean }>('/lab/reset', { method: 'POST' }),

  listPartialBookings: (userId: number) =>
    request<BookingAttempt[]>(`/ops/partial-bookings?user_id=${userId}`),

  getRequestTimeline: (requestId: number, userId: number) =>
    request<TimelineEvent[]>(`/ops/requests/${requestId}/timeline?user_id=${userId}`),
};
