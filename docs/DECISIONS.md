# Decision Log

Running record of what we decided, the options considered, and why — built up section
by section as we work through the assignment. This doubles as prep for the required
"Methodology report" deliverable (assignment Section 14).

## Format per entry
- **Decision:**
- **Options considered:**
- **Why this one / why the others fell behind:**
- **Open questions / revisit later:**

---

## Timeline

- Received: Wednesday night, 2026-11-18.
- Demo: following Wednesday night, 2026-11-25 (7-calendar-day window per the brief).
- Section 02 demo travel dates must be at least 30 days after the submission date,
  so pick outbound dates on/after **2026-12-25** to be safely clear of the boundary.

## Stack (initial decision, backend settled / frontend+infra open)

- **Backend: Python + FastAPI.** User's explicit preference, also consistent with the
  rest of this portfolio's stack (Learndata, Economic Ripple) - no need to relitigate.
- **Frontend, DB, scheduler/queue, hosting: open - see "Open items" below.**
- No AWS/cloud-provider infra for this project (confirmed with user 2026-11-19): the
  global CLAUDE.md's infra-gate rules are scoped to company work, not this personal
  assignment. Hosting here follows the same lightweight PaaS pattern as Economic
  Ripple (Vercel/Render-style), not AWS/GCP/Azure.

## Section 01 - The objective

**What it actually asks for, stripped to the mechanism:** a system that (1) takes a
structured trip request, (2) periodically prices it against real inventory, (3) alerts
the owning user the moment a complete, valid package crosses their budget (or drops
meaningfully further), and (4) lets them convert that alert into a simulated booking
that behaves like a real one would under concurrency, expiry, and partial failure.

**Reconciling the friend's pointers against the actual brief:**
- *Competitor research / which APIs* -> this is Section 04 (data sourcing), not
  optional - 20% of the grade is "source research and price/data integrity." Needs
  real investigation, not a quick pick.
- *"Logical watcher"* -> Section 06's monitoring scheduler (5-min cycle + manual
  trigger + audit trail). This is the system's heartbeat; everything downstream
  depends on it persisting observations correctly.
- *Browse-then-price-drops notification* -> related concept, but the brief's actual
  mechanism (Section 07) is stricter and more specific: first budget-crossing alert,
  then only re-alert on 5%+ further improvement, reset only by a valid above-budget
  observation (never by a failed check). This specific state machine is what gets
  graded, not a generic "price went down, notify" rule.
- *Load balancer / domain / hosting* -> Section 14's "Runnable product" deliverable.
  Real, but low weight relative to correctness, and explicitly not AWS here.
- *loguru / log schema* -> supports the Section 06 audit trail and Section 10
  "operations view." Good practice, worth doing, but in service of monitoring
  correctness - not a separate grading line.
- *CI/CD, configmaps/secrets split* -> supports the Section 14 "Code repository"
  deliverable (config example without secrets). Worth real CI (tests on push), lighter
  on the secrets-management ceremony given this is a solo prototype, not a multi-env
  rollout.
- *SDLC starting from data* -> matches the brief's own ordering almost exactly
  (Section 04 data -> 05 packages -> 06 monitor -> 07 notify -> 08-09 booking). Good
  instinct, and it's the order we'll actually work through section by section.

**What "absolute base" (pre-everything-else MVP) has to mean, given the grading
weights (30% booking correctness/concurrency/recovery, 20% source research, 20%
monitoring/notification, 15% tests, 10% methodology, 5% usability):** the base slice is
not "a working UI" - it's one request, one real (or honestly-labeled simulated)
pricing source per category, a correct monitor-alert cycle, and a booking flow that
survives the failure-mode table in Section 09. UI and breadth of sources are what we
add once that core loop is provably correct, not before.

## Open items for this round of discussion

1. **Frontend**: plain React+Vite+TS vs. Next.js vs. server-rendered (Jinja2/HTMX on
   FastAPI). Leaning toward React+Vite over Next.js - this is an authenticated
   dashboard app with no SEO/marketing surface, so SSR buys nothing, and a simpler
   client avoids extra framework surface to defend in the Section 13 live review. Open
   to discussion.
2. **Database**: Postgres is the strong default - the concurrency scenarios (Section
   09's "last room contention," idempotent retries, hold expiry) want real
   transactions and row locking, which a document store makes harder to get right, not
   easier.
3. **Scheduler/queue for the 5-minute monitor**: in-process APScheduler (simple, no
   extra infra) vs. Celery+Redis (more "real," more to explain/justify for a prototype
   this size). Leaning APScheduler for v1 given the time budget, revisit if the load
   test (Section 12, 100 requests/3 cycles) shows it doesn't hold up.
4. **Data sources per category** (flights/hotels/cabs) - needs its own dedicated
   research pass before deciding; not guessing this one, will investigate properly.
