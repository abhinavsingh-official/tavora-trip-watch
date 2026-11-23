# Demo and Handover

## 1. Live demo and local setup

**Live demo**: https://tavora-frontend-2ldl.onrender.com (backend:
https://tavora-backend-fm0b.onrender.com), deployed on Render's free tier.
**Hosting restriction**: the free backend spins down after 15 minutes idle;
the first request after that takes ~30-60s to wake it up — if the demo looks
unresponsive at first, this is why, not a defect.

**Local setup**: see `backend/README.md` and `frontend/README.md` for exact
commands (`pip install -r requirements.txt`, Postgres connection string in
`.env`, `alembic`/create-schema step, `uvicorn app.main:app --reload`;
`npm install && npm run dev` for the frontend). `backend/scripts/seed.py`
seeds all three mock users' required requests in one run.

## 2. 5–8 minute walkthrough script

**0:00–0:30 — Orientation.** Open the Home page (`/`) — point out this is
the real entry point, with a live profile card per mock user. Click "View
as User A" to enter their Dashboard, and point out the user switcher (top
right) and the nav: Home, Dashboard, Notifications, Ops, Scenario Lab
(dashed border — explicitly marked as demo-only tooling).

**0:30–2:00 — The core loop, live.** On User A's Mumbai⇄Goa request, click
"Check price now" — a real Sabre + Hotelbeds call happens live (~10-15s).
Show the itemized breakdown (flight out/return, hotel, cab out/return,
taxes) and the price-history chart. Click **"View trip story"** — show the
real alternative flights and hotels that check actually found (up to 5 of
each), with the cheapest eligible one visibly marked "Picked"; point out
this costs zero extra supplier calls, since it's reading the same raw
response already stored. Back on the Dashboard, open the Scenario Lab, use **price
override** to force a below-budget total, go back to Dashboard, trigger a
manual cycle (or wait for the real alert to fire from the override), and
open the resulting Notification — point out it's scoped to User A only
(switch to User B, show their inbox is empty for this alert).

**2:00–3:30 — Offer review and the real hold.** Click "Review & book" on the
alert. Point out this re-fetches a *fresh* quote live (not the cached alert
price) and shows both the original and current total side by side. Point out
the 2-minute countdown. Explain: the countdown is corrected against the
Scenario Lab's own clock on load, so a prior clock-advance doesn't make it
look pre-expired.

**3:30–4:30 — Hold expiry, scenario 3.** Use **clock-advance** (+3 minutes)
after opening a review, then attempt to book — show the explicit
hold-expired rejection, not a silent failure or a stale-price acceptance.

**4:30–6:00 — The failure scenarios.** Start a fresh review, use
**force-failure** on the hotel component, then book. Show the result: flight
`confirmed`→`cancelled` (compensated), hotel `failed`, cab `pending` (never
attempted), aggregate `partial`. Navigate to **Ops** — show this booking
listed under unresolved partial bookings, open its event timeline, and point
out the timeline merges three separate tables (observations, notifications,
bookings) into one time-ordered feed. Then show the two harder cases: arm a
**timeout** on a component and book — the result is `needs_reconciliation`,
a second booking attempt on the same offer returns the identical stuck row
(no duplicate), and the Booking Result page's reconcile action is the only
way to resolve it either direction. Separately, arm **restart-after** on a
component and book — the result stops at `in_progress`; booking the same
offer again resumes and finishes it, still the same booking ID.

**6:00–7:00 — Breadth.** Switch to User B (4 adults, 2 rooms) — run a real
check, show the raw response actually reflects 2-room/4-adult occupancy
pricing and the tempo-traveller cab rate, not the sedan rate. Edit User A's
request's budget — show a previously-held offer's hold is cleared
immediately by the edit.

**7:00–8:00 — Close.** State the honest gaps aloud (§5 of
`docs/VERIFICATION_PACKAGE.md`): cab prices are simulated (and visibly
labeled as such) since no reachable real fare API exists for that category;
visual polish was deliberately left last per the assignment's own stated
priority; the free-tier backend sleeps after 15 minutes idle.

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
- Visual polish, the one item left after V4 closed out the remaining
  failure-table rows and the 100-request load test.

## 5. AI-assistance disclosure

This project was built using Claude Code (Anthropic) throughout — as a
pair-programming tool for implementation, code review, and documentation
drafting, under continuous direction and review by the candidate. Concretely:

- All architectural, source-selection, and scope-prioritization decisions
  (recorded in `docs/DECISIONS.md`, dated and cumulative) were made and
  owned by the candidate; Claude Code was used to research options, draft
  code implementing decisions already made, and surface trade-offs for the
  candidate to decide on.
- Every data-source claim in `docs/research_summary.md` and
  `docs/DATA_SOURCE_DOSSIER.md` was verified against real registration
  attempts and real API calls — not accepted from documentation or model
  output alone. Four real access attempts (Duffel, Sabre, Hotelbeds,
  RateHawk) directly settled questions that documentation review alone left
  ambiguous.
- Every feature claimed as working was verified against a real running
  system before being reported as done: real curl calls against the live
  deployed backend, the full automated pytest suite (39 tests, rerun fresh
  for this document — see `docs/VERIFICATION_PACKAGE.md` §1), and real
  headless-browser runs exercising the actual UI, not just code inspection.
- A full adversarial security/correctness review was run against the
  codebase mid-project specifically to find what AI-assisted code might
  have missed; it found and the candidate fixed a real cross-user data
  exposure (missing ownership checks on several endpoints) and a scheduler
  error-handling bug — both verified fixed against the live system
  afterward, not just re-read.
- The candidate is responsible for, and can explain and defend, every
  decision and every line of code in this submission, consistent with §13's
  requirement.
