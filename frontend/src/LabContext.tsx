import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from './api';
import { useCurrentUser } from './UserContext';
import type { LabBookingOutcome, LabComponent, SimulationLogEntryOut, TripRequest } from './types';

interface LabContextValue {
  scenarioUserId: number | null;
  scenarioRequests: TripRequest[];
  requestId: number | null;
  setRequestId: (id: number) => void;
  cancelledCount: number;
  refreshScenarioRequests: () => void;
  addSimulatedRequest: () => Promise<void>;
  addBusy: boolean;

  // Bumped by every lever below; Lab.tsx watches this to refetch its results without knowing about the sidebar
  version: number;
  message: string | null;
  busy: boolean;
  now: string | null;
  log: SimulationLogEntryOut[];

  shockFraction: number;
  setShockFraction: (f: number) => void;
  shockBusy: boolean;

  advanceMinutes: string;
  setAdvanceMinutes: (v: string) => void;
  handleAdvanceClock: () => Promise<void>;
  handleTriggerCycle: () => Promise<void>;
  handleMutatePrices: () => Promise<void>;

  overrideComponent: LabComponent;
  setOverrideComponent: (c: LabComponent) => void;
  overridePrice: string;
  setOverridePrice: (v: string) => void;
  handleOverride: () => Promise<void>;

  failComponent: LabComponent;
  setFailComponent: (c: LabComponent) => void;
  failOutcome: LabBookingOutcome;
  setFailOutcome: (o: LabBookingOutcome) => void;
  handleFailComponent: () => Promise<void>;

  cancelFailComponent: LabComponent;
  setCancelFailComponent: (c: LabComponent) => void;
  handleCancelFailure: () => Promise<void>;

  restartAfterComponent: LabComponent;
  setRestartAfterComponent: (c: LabComponent) => void;
  handleRestartAfter: () => Promise<void>;

  priceCheckTimeoutComponent: LabComponent;
  setPriceCheckTimeoutComponent: (c: LabComponent) => void;
  handlePriceCheckTimeout: () => Promise<void>;

  sharedRoomIds: number[];
  toggleSharedRoomId: (id: number) => void;
  sharedRoomCount: string;
  setSharedRoomCount: (v: string) => void;
  handleSharedRoomScenario: () => Promise<void>;

  handleReset: () => Promise<void>;
  handleClearLog: () => Promise<void>;
}

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

export function LabProvider({ children }: { children: ReactNode }) {
  const { users } = useCurrentUser();
  const scenarioUser = users.find((u) => u.name === 'Scenario');

  const [scenarioRequests, setScenarioRequests] = useState<TripRequest[]>([]);
  const [cancelledCount, setCancelledCount] = useState(0);
  const [requestId, setRequestIdState] = useState<number | null>(null);
  const [addBusy, setAddBusy] = useState(false);

  const [version, setVersion] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState<string | null>(null);
  const [log, setLog] = useState<SimulationLogEntryOut[]>([]);

  const [shockFraction, setShockFraction] = useState(0);
  const [shockBusy, setShockBusy] = useState(false);

  const [advanceMinutes, setAdvanceMinutes] = useState('3');
  const [overrideComponent, setOverrideComponent] = useState<LabComponent>('flight');
  const [overridePrice, setOverridePrice] = useState('');
  const [failComponent, setFailComponent] = useState<LabComponent>('hotel');
  const [failOutcome, setFailOutcome] = useState<LabBookingOutcome>('fail');
  const [cancelFailComponent, setCancelFailComponent] = useState<LabComponent>('flight');
  const [restartAfterComponent, setRestartAfterComponent] = useState<LabComponent>('flight');
  const [priceCheckTimeoutComponent, setPriceCheckTimeoutComponent] = useState<LabComponent>('hotel');
  const [sharedRoomIds, setSharedRoomIds] = useState<number[]>([]);
  const [sharedRoomCount, setSharedRoomCount] = useState('1');

  function refreshScenarioRequests() {
    if (scenarioUser === undefined) return;
    api.listRequests(scenarioUser.id).then((all) => {
      const reqs = all.filter((r) => r.status !== 'cancelled');
      setCancelledCount(all.length - reqs.length);
      setScenarioRequests(reqs);
      setRequestIdState((prev) => (reqs.some((r) => r.id === prev) ? prev : (reqs[0]?.id ?? null)));
    });
  }

  function refreshLog() {
    api.labLog().then(setLog);
  }

  useEffect(refreshScenarioRequests, [scenarioUser]);

  useEffect(() => {
    api.labClock().then((c) => setNow(c.now));
    refreshLog();
  }, []);

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

  useEffect(() => {
    setShockFraction(0);
  }, [requestId]);

  useEffect(() => {
    if (requestId === null || shockFraction === 0) return;
    setShockBusy(true);
    const timer = window.setTimeout(() => {
      api
        .labShockAndCheck(requestId, shockFraction)
        .then(() => {
          setVersion((v) => v + 1);
          refreshLog();
        })
        .finally(() => setShockBusy(false));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [shockFraction, requestId]);

  async function withBusy(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
      setVersion((v) => v + 1);
    } finally {
      setBusy(false);
      refreshLog();
    }
  }

  async function handleAdvanceClock() {
    await withBusy(async () => {
      const minutes = Number(advanceMinutes) || 0;
      const result = await api.labAdvanceClock(minutes);
      setNow(result.now);
      setMessage(`Clock moved forward ${minutes} minute(s).`);
    });
  }

  async function handleTriggerCycle() {
    await withBusy(async () => {
      const result = await api.labTriggerCycle();
      setMessage(`Ran the cycle now. Checked: ${result.checked_request_ids.join(', ') || 'none active'}.`);
    });
  }

  async function handleMutatePrices() {
    await withBusy(async () => {
      const result = await api.labMutatePrices();
      setMessage(
        `Nudged ${result.flights_mutated} flight(s), ${result.cabs_mutated} cab(s), ${result.hotels_mutated} hotel(s).`,
      );
    });
  }

  async function handleOverride() {
    if (requestId === null) return;
    await withBusy(async () => {
      const value = Number(overridePrice) || 0;
      await api.labOverride(requestId, overrideComponent, value);
      setMessage(`Next check will use ₹${value} for ${overrideComponent}.`);
    });
  }

  async function handleFailComponent() {
    if (requestId === null) return;
    await withBusy(async () => {
      await api.labFailComponent(requestId, failComponent, failOutcome);
      setMessage(`Next booking will make ${failComponent} ${failOutcome}.`);
    });
  }

  async function handleCancelFailure() {
    if (requestId === null) return;
    await withBusy(async () => {
      await api.labCancelFailure(requestId, cancelFailComponent);
      setMessage(`${cancelFailComponent}'s next compensating cancellation will itself fail.`);
    });
  }

  async function handleRestartAfter() {
    if (requestId === null) return;
    await withBusy(async () => {
      await api.labRestartAfter(requestId, restartAfterComponent);
      setMessage(`Next booking stops right after ${restartAfterComponent} confirms.`);
    });
  }

  async function handlePriceCheckTimeout() {
    if (requestId === null) return;
    await withBusy(async () => {
      await api.labPriceCheckTimeout(requestId, priceCheckTimeoutComponent);
      setMessage(`Next price check will time out on ${priceCheckTimeoutComponent} - total shows "provisional".`);
    });
  }

  function toggleSharedRoomId(id: number) {
    setSharedRoomIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function handleSharedRoomScenario() {
    if (sharedRoomIds.length < 2) {
      setMessage('Pick at least two simulated users to race against each other.');
      return;
    }
    await withBusy(async () => {
      const rooms = Number(sharedRoomCount) || 0;
      await api.labSharedRoomScenario(sharedRoomIds, rooms);
      setMessage(`Requests ${sharedRoomIds.join(', ')} are racing for ${rooms} room(s).`);
    });
  }

  async function handleReset() {
    await withBusy(async () => {
      await api.labReset();
      setMessage('Cleared every override, scheduled failure, and the clock.');
      api.labClock().then((c) => setNow(c.now));
    });
  }

  async function handleClearLog() {
    await withBusy(async () => {
      await api.labLogClear();
      setMessage('Cleared the activity log.');
    });
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
        version,
        message,
        busy,
        now,
        log,
        shockFraction,
        setShockFraction,
        shockBusy,
        advanceMinutes,
        setAdvanceMinutes,
        handleAdvanceClock,
        handleTriggerCycle,
        handleMutatePrices,
        overrideComponent,
        setOverrideComponent,
        overridePrice,
        setOverridePrice,
        handleOverride,
        failComponent,
        setFailComponent,
        failOutcome,
        setFailOutcome,
        handleFailComponent,
        cancelFailComponent,
        setCancelFailComponent,
        handleCancelFailure,
        restartAfterComponent,
        setRestartAfterComponent,
        handleRestartAfter,

        priceCheckTimeoutComponent,
        setPriceCheckTimeoutComponent,
        handlePriceCheckTimeout,
        sharedRoomIds,
        toggleSharedRoomId,
        sharedRoomCount,
        setSharedRoomCount,
        handleSharedRoomScenario,
        handleReset,
        handleClearLog,
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
