# Demo and Handover

## 1. Live demo and local setup

**Live demo**: https://tavora-frontend-2ldl.onrender.com (backend:
https://tavora-backend-fm0b.onrender.com), deployed on Render's free tier.
**Hosting restriction**: the free backend spins down after 15 minutes idle;
the first request after that takes ~30-60s to wake it up — if the demo looks
unresponsive at first, this is why, not a defect.

**Local setup**: see `backend/README.md` and `frontend/README.md` for exact
commands (`pip install -r requirements.txt`, Postgres connection string in
`.env`, `uvicorn app.main:app --reload`; `npm install && npm run dev` for
the frontend). `backend/scripts/seed.py` brings the schema up to date via
real Alembic migrations (`backend/alembic/`, added V7) and seeds the three
mock users' required requests plus a fourth "Scenario" user the Simulation
page runs its demos against (see §2's Simulation step below) in one run -
no separate manual schema-creation step. CI (`.github/workflows/ci.yml`)
runs the backend test suite against a real Postgres service container plus
a dedicated fresh-database migration check, and the frontend
type-check/build, on every push and PR to `main` - currently green.

## 2. 5–8 minute walkthrough script

**0:00–0:30 — Orientation.** Open the Home page (`/`) — a plain landing page
(hero + "how it works"), not the user's own data; that's the Dashboard's
job. Point out the sidebar: "Viewing as" the current mock user, a switcher
to jump between User A/B/C. Point out the header nav: Home, Dashboard, New
request, Simulation (dashed border when open - explicitly marked as
demo-only tooling), then a Trash icon and a bell icon on the far right -
cancelling a request moves it there instead of deleting it, and alerts
live in the bell's dropdown instead of a separate Notifications tab.

**0:30–2:00 — The core loop, live.** Go to the Dashboard as User A, and on
their Mumbai⇄Goa request click "Check price now" a few times - a real
price check happens live each time. Show the itemized breakdown, the
latest-valid and lowest-observed-valid totals, and the real price-history
chart (with a budget reference line and real axis numbers) building up
across checks - also point out the "checked X ago" label, which flags a
total as potentially out of date even without an edit, since the
background market can move between checks. Click **"Your bookings"** -
show the itemized Overview & pay tab, then toggle **"Browse the specific
options"** to show the real hotel/flight/cab candidates this request's
monitoring actually found, with the cheapest eligible one in each list
marked "Cheapest found." Point out the two ways to actually purchase: pay
against a held alert, or click **"Buy now at today's price"** to check and
book in one click without waiting for an alert at all.

**2:00–3:30 — Offer review and the real hold.** Trigger a below-budget
alert (see §3's Simulation step below for the fastest way), open it from
the bell dropdown. Point out this re-fetches a *fresh* quote live (not the
cached alert price) and shows both the original and current total side by
side. Point out the 2-minute countdown, then click **"Confirm booking
(simulated)"**.

**3:30–7:00 — The Simulation page.** Open **Simulation**. The left sidebar
is the whole control panel: pick or **"+ Add a simulated trip"** for a
simulated user (always its own plain request, never touching User A/B/C),
then drag **"Shock the market"** - this applies an exact, guaranteed price
move to that trip's own market and re-checks immediately, which is the
fastest way to produce a below-budget alert for the walkthrough above. The
center column shows the result: price breakdown, the same chart, simulated
notifications, and a real persisted activity log; the right panel is a
live Timeline. Expand **Booking scenarios** in the sidebar to show the
harder cases, each followed by clicking **Book now** in the center panel:
- Schedule a booking failure on the hotel component, then Book now - flight
  `confirmed`→`cancelled` (compensated), hotel `failed`, cab `pending`
  (never attempted), aggregate `partial`. Back on the Dashboard, point out
  the **"Needs attention"** card that now appears above the request list.
- "Supplier never responds" on a component, then Book now - the result is
  `needs_reconciliation`; a second Book now on the same offer returns the
  identical stuck row (no duplicate); the Booking Result page's reconcile
  action is the only way to resolve it.
- Simulate a restart mid-booking on a component, then Book now twice - the
  first stops at `in_progress`, the second resumes and finishes it, same
  booking ID.
- The shared-room race: check two simulated users, set 1 room available,
  book each in turn - only the first gets it; the second gets a real
  `unavailable` on its hotel.

**7:00–8:00 — Breadth and close.** Switch to User B (4 adults, 2 rooms) -
run a real check, show the response reflects 2-room/4-adult occupancy
pricing and the tempo-traveller cab's distance-based rate, not the sedan
rate. Edit User A's request's budget - show a previously-held offer's hold
is cleared immediately by the edit. Cancel a request, then open the Trash
icon and restore it, to show cancelling isn't a dead end. State the honest
gaps aloud (§3 of `docs/VERIFICATION_PACKAGE.md`): cab prices are
simulated since no reachable real fare API exists for that category,
though each one is a real per-km rate times an assumed transfer distance;
the simulated clock is a single global offset, not scoped per-user, so
advancing it in Simulation also shifts timestamps app-wide; the free-tier
backend sleeps after 15 minutes idle.

## 3. Known issues

See `docs/VERIFICATION_PACKAGE.md` §5 for the full consolidated list,
summarized here:
- `provisional` component status is schema-forward, not yet reachable by any
  real code path (every real source only ever returns `complete` or
  `unavailable` today).
- Cache/rate-limit state is per-process, not shared — a real limit beyond a
  single worker process, not yet hit at this project's scale.
- Hotelbeds' EUR→INR conversion uses one fixed documented rate, not a live
  FX feed.
- Free-tier backend sleeps after 15 min idle (first request after is slow).
- Visual polish deliberately left last, unchanged since V1.
- One shared package-level hold rather than independently-tracked
  per-component hold expiries (Sec. 08) - satisfies the literal requirement
  by construction, but noted explicitly rather than left implicit; see
  `docs/versions/V7.md` §8.
- The simulated clock (`app/sim_clock.py`) is one global offset, not scoped
  per user - advancing it on the Simulation page shifts "now" for every
  request app-wide, including User A/B/C's, not just the simulated one.

A full audit (`docs/internal/audit-log-2026-11-23.md`) found and V7 fixed 11 real
issues, most notably a cancelled/paused request that could still be
reviewed and fully booked, and a Scenario Lab price override that wasn't
actually deterministic. All 11 are fixed, live-verified, and
regression-tested - see that document and `docs/versions/V7.md` for the
full record, including a further gap (Sec. 06's lowest-total/price-history
chart) found and fixed during a fresh requirements re-read.

## 4. What would be needed for production

- A real payment/booking relationship with Sabre, Hotelbeds (or a GDS/
  aggregator with contracted real fares, not a test cell) and a real cab
  supplier (Ola Outstation, CabBazar — both real, documented, but
  partnership-gated; see `docs/DATA_SOURCE_DOSSIER.md` §3).
- A horizontally-scalable scheduler (Celery+Redis or similar) once request
  volume exceeds what one in-process APScheduler can process inside its own
  interval — reasoned, not measured, in `docs/VERIFICATION_PACKAGE.md` §3.
- Shared (not per-process) caching/rate-limiting once more than one backend
  worker process runs.
- Real authentication (this prototype uses a mock-user switcher by design,
  per §03's own "a simple mock-user switcher is sufficient").
- A live FX feed in place of the one fixed EUR→INR rate.
- Independently-tracked per-component hold expiries, if a real product
  needed holds that could genuinely differ in length per supplier - this
  prototype's single shared hold is a deliberate simplification (see
  `docs/versions/V7.md` §8).
- Visual polish - the one functional item left; everything else found by
  the full audit (`docs/internal/audit-log-2026-11-23.md`) and the V7 requirements
  re-read has been fixed.

## 5. AI-assistance disclosure

This project was built using Claude Code (Anthropic) throughout — as a
pair-programming tool for implementation, code review, and documentation
drafting, under continuous direction and review by the candidate. Concretely:

- All architectural, source-selection, and scope-prioritization decisions
  (recorded in `docs/internal/decision-log.md`, dated and cumulative) were made and
  owned by the candidate; Claude Code was used to research options, draft
  code implementing decisions already made, and surface trade-offs for the
  candidate to decide on.
- Every data-source claim in `docs/internal/research-summary.md` and
  `docs/DATA_SOURCE_DOSSIER.md` was verified against real registration
  attempts and real API calls — not accepted from documentation or model
  output alone. Four real access attempts (Duffel, Sabre, Hotelbeds,
  RateHawk) directly settled questions that documentation review alone left
  ambiguous.
- Every feature claimed as working was verified against a real running
  system before being reported as done: real curl calls against the live
  deployed backend, the full automated pytest suite (91 tests, rerun fresh
  for this document — see `docs/VERIFICATION_PACKAGE.md` §1), and real
  headless-browser runs exercising the actual UI, not just code inspection.
- A full adversarial security/correctness review was run against the
  codebase mid-project specifically to find what AI-assisted code might
  have missed; it found and the candidate fixed a real cross-user data
  exposure (missing ownership checks on several endpoints) and a scheduler
  error-handling bug — both verified fixed against the live system
  afterward, not just re-read.
- A second, more exhaustive audit (`docs/internal/audit-log-2026-11-23.md`, 4 passes:
  live walkthrough, backend code read, frontend code read, re-verification)
  found 11 further issues, most notably a cancelled/paused request that
  could still be reviewed and fully booked, and a Scenario Lab override
  that wasn't actually deterministic - every one reproduced live before
  being fixed, every fix re-verified live afterward, and three false leads
  (a misread alert-dedup case, a screenshot rendering artifact, a
  test-timing false alarm) were caught and discarded during that same
  process rather than reported as bugs. A subsequent fresh read of the
  assignment's own requirements against the real code (not against this
  document's own prior claims) found one further gap it had missed -
  Sec. 06's lowest-total/price-history chart - fixed the same way.
- A later check specifically on whether CI/CD actually works (not just the
  app) found CI's own Alembic-verification step had been silently failing
  on every run since it was added - `psql` doesn't understand SQLAlchemy's
  `+psycopg2` driver suffix in the connection URL - confirmed via
  `gh run list` showing every prior run red, fixed, and re-verified green.
  Render's actual auto-deploy (the real CD path) was unaffected the whole
  time, confirmed separately via its own deploy history.
- The candidate is responsible for, and can explain and defend, every
  decision and every line of code in this submission, consistent with §13's
  requirement.
