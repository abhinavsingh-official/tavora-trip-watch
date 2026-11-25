# Scenario Guide

How to check all 7 required scenarios yourself on the **Simulation** page (`/lab`). Click
**"Reset everything"** in the sidebar between scenarios to clear any leftover levers.

## 1. Below-budget trip

1. Pick (or **"+ Add a simulated trip"**) a simulated user in the sidebar.
2. Drag **"Shock the market"** to a negative number, e.g. `-20%`.
3. Click **"Check price now"** - it shows up under "Simulated notifications."
4. Click **"Book now"** - flight, hotel, and cab all show `confirmed`.

## 2. Price changes before review

1. Shock the market to one value, click **"Check price now"** - note the total.
2. Shock the market to a *different* value, click **"Check price now"** again - a new total.
3. Click **"Book now"** - the booked total matches the second check, not the first. A stale alert
   price is never auto-honored.

## 3. Hold validity and expiry

1. Switch to a real user (A, B, or C) in the sidebar.
2. On the Dashboard, click **"Check price now"** until an alert shows up under the bell icon.
3. Open it - note the countdown (flight holds for 2 minutes, hotel for 3, cab for 5 - whichever
   expires first is what's shown).
4. Wait at least 2 real minutes without touching anything, then try to confirm the booking - it's
   rejected, naming the flight specifically as the component whose hold expired.

(Note: Simulation's Clock lever on the sandbox page intentionally does **not** speed this up for a
real user anymore - that's the "fast-forwarding affects the whole app" bug fix. Advancing it only
ever moves time for the Simulation page's own Scenario user, never for A/B/C.)

## 4. Last room contention

1. Expand **"Booking scenarios"** in the sidebar.
2. Under "Shared room race," check 2+ simulated users, set rooms to `1`, click **"Race."**
3. Switch to each checked user in turn and click **"Book now."**
4. Exactly one shows `confirmed`; the Shared room race card shows the other's hotel as
   `unavailable`.

## 5. Partial booking failure

1. Expand **"Booking scenarios,"** pick `hotel` + `Rejected outright`, click **"Schedule."**
2. Click **"Book now."**
3. Flight shows `cancelled` (compensated), hotel shows `failed`, cab stays `pending`, aggregate
   is `partial`.
4. Check the Dashboard - a **"Needs attention"** card appears for the affected real user.

## 6. Timeout and restart

**Timeout:** Booking scenarios → pick a component + `Supplier never responds` → Schedule → Book
now - status is `needs_reconciliation`. Click Book now again - same stuck result, no duplicate.
Only the Booking Result page's reconcile button resolves it.

**Restart:** Booking scenarios → "Simulate a restart mid-booking" on a component → Schedule → Book
now - stops at `in_progress`. Click Book now again - it resumes and finishes, same booking ID.

## 7. Monitoring reliability

Click **"Run cycle"** a few times in a row with nothing else changed. The notification list
doesn't grow (no duplicate alerts), and the activity log shows each check without a new alert
unless the price actually moved.
