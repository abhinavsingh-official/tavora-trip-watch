// The only file that knows the backend's URLs. Every page goes through here,
// never calls fetch() directly - see docs/versions/V1_MODULES.md.

import type {
  BookingAttempt,
  LabClock,
  LabComponent,
  Notification,
  NotificationReview,
  PriceObservation,
  TripRequest,
  TripRequestCreate,
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

  listObservations: (requestId: number) =>
    request<PriceObservation[]>(`/requests/${requestId}/observations`),

  checkPrice: (requestId: number) =>
    request<PriceObservation>(`/requests/${requestId}/check`, { method: 'POST' }),

  listNotifications: (userId: number) =>
    request<Notification[]>(`/notifications?user_id=${userId}`),

  reviewNotification: (notificationId: number) =>
    request<NotificationReview>(`/notifications/${notificationId}/review`, {
      method: 'POST',
    }),

  book: (requestId: number, notificationId: number, acceptedTotal: number) =>
    request<BookingAttempt>(`/requests/${requestId}/book`, {
      method: 'POST',
      body: JSON.stringify({
        notification_id: notificationId,
        accepted_total: acceptedTotal,
      }),
    }),

  getBooking: (bookingId: number) =>
    request<BookingAttempt>(`/bookings/${bookingId}`),

  labClock: () => request<LabClock>('/lab/clock'),

  labOverride: (requestId: number, component: LabComponent, price: number) =>
    request<{ ok: boolean }>('/lab/override', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, component, price }),
    }),

  labReset: () => request<{ ok: boolean }>('/lab/reset', { method: 'POST' }),
};
