# Demo and Handover

## 1. Live demo and local setup

**Live demo**: https://tavora-frontend-2ldl.onrender.com (backend:
https://tavora-backend-fm0b.onrender.com), Render free tier. Backend sleeps
after 15 min idle - first request after that takes ~30-60s to wake it up.

**Local setup**: see `backend/README.md` / `frontend/README.md` for exact
commands. `backend/scripts/seed.py` runs Alembic migrations and seeds the
three mock users plus a "Scenario" user (used by the Simulation page) in one
run. CI (`.github/workflows/ci.yml`) runs backend tests against a real
Postgres container, a fresh-database migration check, and the frontend
build, on every push/PR to `main` - currently green.

## 2. 5-8 minute walkthrough script

**0:00-0:30 - Orientation.** Open Home (`/`) - a plain landing page, not the
user's data. Point out the sidebar ("Viewing as" + User A/B/C switcher) and
header nav (Home, Dashboard, New request, Simulation, Trash, bell).

**0:30-2:00 - The core loop.** Dashboard as User A, Mumbai⇄Goa request,
click "Check price now" a few times - a real price check each time. Show
the itemized breakdown, latest/lowest totals, the price-history chart, and
the "checked X ago" staleness label. Click **"Your bookings"** - show the
Overview & pay tab, toggle **"Browse the specific options"** for the real
hotel/flight/cab candidates ("Cheapest found" marked). Point out the two
ways to buy: pay a held alert, or **"Buy now at today's price"** (checks and
books in one click, no alert needed).

**2:00-3:30 - Offer review and the hold.** Trigger a below-budget alert (see
3:30 below), open it from the bell. Show it re-fetches a *fresh* quote
(original vs. current total side by side) and the 2-minute countdown, then
click **"Confirm booking (simulated)"**.

**3:30-7:00 - The Simulation page.** Open **Simulation** - left sidebar is
the whole control panel: pick or **"+ Add a simulated trip"**, then drag
**"Shock the market"** for an instant guaranteed price move (fastest way to
trigger the alert above). Center column: price breakdown, chart,
notifications, activity log. Right: live Timeline. Expand **Booking
scenarios** and click **Book now** for each:
- Fail the hotel component, Book now - flight `cancelled` (compensated),
  hotel `failed`, cab `pending`, aggregate `partial`. Dashboard now shows
  **"Needs attention"**.
- "Supplier never responds", Book now - `needs_reconciliation`; a second
  Book now returns the same stuck row (no duplicate); only the Booking
  Result page's reconcile action resolves it.
- Restart mid-booking, Book now twice - first stops at `in_progress`,
  second resumes to completion, same booking ID.
- Shared-room race: check two simulated users, set 1 room, book each in
  turn - only the first succeeds; the second gets a real `unavailable`.

**7:00-8:00 - Breadth and close.** User B (4 adults, 2 rooms) - a real check
shows 2-room/4-adult pricing and the tempo-traveller cab rate. Edit User A's
budget - a held offer's hold clears immediately. Cancel a request, restore
it from Trash. State the honest gaps (see §3): cab prices are simulated;
the simulated clock is global, not per-user; free tier sleeps after 15 min.

## 3. Known issues

Full list: `docs/VERIFICATION_PACKAGE.md` §5. Summary:
- `provisional` status is schema-forward, not reachable by any real path yet.
- Cache/rate-limit state is per-process, not shared across workers.
- Hotelbeds EUR→INR uses one fixed rate, not a live FX feed.
- Free-tier backend sleeps after 15 min idle.
- Visual polish deliberately left last.
- One shared package-level hold, not independently-tracked per-component
  holds (Sec. 08) - satisfies the literal requirement by construction; see
  `docs/versions/V7.md` §8.
- The simulated clock is one global offset - advancing it shifts "now" for
  every user, not just the simulated one.

A full audit (`docs/internal/audit-log-2026-11-23.md`) found and V7 fixed 11
issues, most notably a cancelled/paused request that could still be booked,
and a non-deterministic Lab price override. All fixed and regression-tested.

## 4. What would be needed for production

- A real payment relationship with Sabre/Hotelbeds (or a contracted GDS) and
  a real cab supplier (Ola Outstation, CabBazar - both partnership-gated).
- A horizontally-scalable scheduler (Celery+Redis) past what one in-process
  APScheduler can handle - see `docs/VERIFICATION_PACKAGE.md` §3.
- Shared, not per-process, caching/rate-limiting across workers.
- Real authentication (this prototype uses a mock-user switcher by design).
- A live FX feed in place of the fixed EUR→INR rate.
- Independently-tracked per-component hold expiries, if suppliers needed
  genuinely different hold lengths - see `docs/versions/V7.md` §8.
- Visual polish - the one functional item left.

## 5. AI-assistance disclosure

Built using Claude Code (Anthropic) throughout as a pair-programming tool,
under the candidate's continuous direction and review:

- Every architectural, source-selection, and scope decision was made and
  owned by the candidate (`docs/internal/decision-log.md`); Claude Code
  researched options and drafted code for decisions already made.
- Every data-source claim (`docs/internal/research-summary.md`,
  `docs/DATA_SOURCES.md`) was verified via real registration and real API
  calls, not accepted from documentation or model output alone - 4 real
  access attempts (Duffel, Sabre, Hotelbeds, RateHawk) settled ambiguous
  questions.
- Every feature was verified against a real running system before being
  called done: real curl calls, the full pytest suite (91 tests - see
  `docs/VERIFICATION_PACKAGE.md` §1), real headless-browser runs.
- A mid-project adversarial review found and fixed a real cross-user data
  exposure (missing ownership checks) and a scheduler error-handling bug,
  both re-verified live afterward.
- A second, 4-pass audit (`docs/internal/audit-log-2026-11-23.md`) found 11
  further issues - notably a cancelled/paused request still bookable, and a
  non-deterministic Lab override - each reproduced live, fixed, and
  re-verified; 3 false leads were caught and discarded rather than reported
  as bugs. A later requirements re-read found one more gap (Sec. 06's
  price-history chart), fixed the same way.
- A CI health check found its own Alembic-verification step had silently
  failed on every run (`psql` doesn't understand the `+psycopg2` driver
  suffix) - confirmed via `gh run list`, fixed, re-verified green. Render's
  actual auto-deploy was unaffected throughout.
- The candidate is responsible for, and can explain and defend, every
  decision and every line of code in this submission, per §13.
