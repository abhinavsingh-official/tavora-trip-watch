import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from './api';
import { useCurrentUser } from './UserContext';
import type { TripRequest } from './types';

interface LabContextValue {
  scenarioUserId: number | null;
  scenarioRequests: TripRequest[];
  requestId: number | null;
  setRequestId: (id: number) => void;
  cancelledCount: number;
  refreshScenarioRequests: () => void;
  addSimulatedRequest: () => Promise<void>;
  addBusy: boolean;
}

/*
 * A simulated trip is never copied from a preset or from User A/B/C - it
 * always starts as its own plain, generic request (same shape the real
 * "+ New request" form would produce), so there's no path left where
 * creating one could land on - or be confused with - a real person's data.
 */
const NEW_SIMULATED_TRIP = {
  origin: 'Mumbai',
  destination: 'Goa',
  outbound_date: '2026-12-26',
  return_date: '2026-12-29',
  adults: 2,
  rooms: 1,
  budget_inr: 35000,
  max_stops_outbound: 2,
  max_stops_return: 2,
  min_star_rating: 0,
  checked_baggage: false,
};

const LabContext = createContext<LabContextValue | null>(null);

/*
 * Lives above the whole app (next to UserProvider) rather than inside the
 * Lab page itself, because the Sidebar needs to show and control "which
 * simulated user" - the Simulation page's controls moved into the Sidebar
 * so the Lab page itself can be the actual content (bookings, notifications,
 * timeline) instead of a settings panel sitting on top of it.
 */
export function LabProvider({ children }: { children: ReactNode }) {
  const { users } = useCurrentUser();
  const scenarioUser = users.find((u) => u.name === 'Scenario');

  const [scenarioRequests, setScenarioRequests] = useState<TripRequest[]>([]);
  const [cancelledCount, setCancelledCount] = useState(0);
  const [requestId, setRequestIdState] = useState<number | null>(null);
  const [addBusy, setAddBusy] = useState(false);

  function refreshScenarioRequests() {
    if (scenarioUser === undefined) return;
    api.listRequests(scenarioUser.id).then((all) => {
      /* A cancelled request can't be checked or paid for from the normal UI -
         hidden here the same way it's hidden from the real Dashboard. */
      const reqs = all.filter((r) => r.status !== 'cancelled');
      setCancelledCount(all.length - reqs.length);
      setScenarioRequests(reqs);
      setRequestIdState((prev) => (reqs.some((r) => r.id === prev) ? prev : (reqs[0]?.id ?? null)));
    });
  }

  useEffect(refreshScenarioRequests, [scenarioUser]);

  /*
   * The only safe way to add another simulated trip - "+ New request" in
   * the main nav always creates for whichever REAL person is currently
   * selected (Scenario was deliberately removed from that switcher, see
   * UserContext.tsx), so using that form while meaning to add a simulated
   * one silently polluted a real demo user's own request list instead.
   * This always targets the Scenario user, no matter who's selected, and
   * always creates a brand new, ordinary request - never a copy of a
   * preset or of User A/B/C - so it shows up exactly like any other
   * dashboard trip, no matter how many have already been created.
   */
  async function addSimulatedRequest() {
    if (scenarioUser === undefined) return;
    setAddBusy(true);
    try {
      const created = await api.createRequest({ user_id: scenarioUser.id, ...NEW_SIMULATED_TRIP });
      refreshScenarioRequests();
      setRequestIdState(created.id);
    } finally {
      setAddBusy(false);
    }
  }

  return (
    <LabContext.Provider
      value={{
        scenarioUserId: scenarioUser?.id ?? null,
        scenarioRequests,
        requestId,
        setRequestId: setRequestIdState,
        cancelledCount,
        refreshScenarioRequests,
        addSimulatedRequest,
        addBusy,
      }}
    >
      {children}
    </LabContext.Provider>
  );
}

export function useLab() {
  const ctx = useContext(LabContext);
  if (!ctx) {
    throw new Error('useLab must be used within a LabProvider');
  }
  return ctx;
}
