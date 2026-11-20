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

## Scope reprioritization - plain-language plan + versioned milestones (2026-11-20)

**Decision:** after reading all 15 sections of the assignment in full and reconciling
them against the actual grading weights, the build is split into four stacked
versions (V1-V4) instead of one flat plan - see `docs/SIMPLE_PLAN.md` for the full
plain-language writeup, kept separate from the real assignment PDF on purpose. Each
version is a complete, demoable thing on its own; each adds correctness or breadth to
the one before it, never unrelated new scope.

- **V1** - one mock user, one request, the full pipeline (request -> price -> alert
  -> review -> simulated booking) working once, by hand, happy-path only.
- **V2** - the same pipeline made correct and safe: real 5-minute scheduler, append-
  only observation log, the real alert state machine (first-crossing / 5%-re-alert /
  above-budget-reset / failure-is-inert), real hold+revalidation, and **one** of the
  six booking failure scenarios built end to end (not all six).
- **V3** - breadth: the other two mock users (incl. User B's 4-adult/2-room occupancy
  case), request edit/pause/cancel, a small test suite for the highest-risk rules, and
  the ops view for stuck/partial bookings.
- **V4** - stretch, explicitly first to drop if time runs out: the scenario-runner's
  time/price/failure controls, the remaining five failure scenarios, the 100-request
  load demo, actually registering for and test-calling Hotelbeds/RateHawk, and visual
  polish last.

**Why this order, not the document's own section order:** the grading weights (30%
booking correctness/concurrency/recovery, 20% monitoring/notification correctness)
put more than half the grade on one mechanism - the request -> price -> alert ->
booking loop not breaking - not on breadth of coverage. V1-V2 build and harden exactly
that mechanism once, deeply, before V3 spends effort on breadth, and V4 spends effort
on scale/proof, which is the part most defensible to leave partially done if the
7-day window (on top of a full-time job) runs out.

**Why a separate plain-language document was worth writing, not just this log:**
the candidate's own assessment, reviewing the AI-produced section-by-section
breakdown done earlier - is that it reads a written brief very literally and risks
treating every numeric detail (exactly 5 minutes, exactly 5%, all six failure rows)
as equally load-bearing, when a real live interview is a conversation, not an exam,
and explicitly allows disclosed, honest gaps. `docs/SIMPLE_PLAN.md` exists to correct
for that: same substance, reorganized by what the grading weights say actually
matters, with an explicit "signal vs. noise" section calling out where the literal
reading overweights detail relative to how the live review will likely probe it.

**What stays true regardless of which version gets reached:** the standing habits -
keep `DECISIONS.md`/`NOTES.md` current as real decisions are made, never leave a gap
undocumented, don't build beyond what's asked, and be able to explain the current
state out loud before moving to the next version - are not scoped to any one version;
they run for the full 7 days.
