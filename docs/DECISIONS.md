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

## Architecture - backend, database, frontend (2026-11-20)

All three previously-open stack questions are now settled, built from V1 onward (not
swapped in later), reasoned through against real alternatives rather than picked by
default.

### Backend: Python + FastAPI (re-confirmed, not just carried over by habit)

**Options considered:** FastAPI, Django+DRF, Node.js (Express/NestJS), Go
(Gin/Echo), Java/Kotlin+Spring Boot.

**Why FastAPI specifically fits this workload:** the system's real work is
I/O-bound, not CPU-bound - most of what it does is wait on outbound calls to
flight/hotel/cab sources, for potentially 100 active requests at once (§12's load
target). FastAPI is `async`-native, so it can hold many of these in flight
concurrently without needing a heavier process/thread model. Pydantic (built in)
gives free, strict request-schema validation that maps directly onto §03's field
list, and auto-generates OpenAPI docs that double as §14's "API contracts" deliverable
input.

**Why the alternatives fell behind, concretely:**
- **Django+DRF** - sync-by-default ORM fights an I/O-heavy workload; its batteries
  (admin panel, full auth system) solve problems this brief explicitly says aren't
  needed ("a simple mock-user switcher is sufficient").
- **Node.js (Express/NestJS)** - architecturally comparable (also event-loop async),
  but no validation layer as strong as Pydantic without bolting one on, and
  materially less hands-on depth than Python for the candidate - a real cost given
  §13's live, unscripted technical review.
- **Go / Java+Spring** - both would genuinely perform better at large scale, but
  cost far more boilerplate to build in a 7-day/full-time-job window, for scale
  (10,000s of req/s) this assignment never actually tests. Directly the kind of
  "complexity and code volume do not earn credit by themselves" trap named in §15.

### Database: Postgres (re-confirmed with a concrete, three-point case)

**Definition:** Postgres (PostgreSQL) is an open-source **relational** database -
data lives in tables with enforced relationships between them, and a group of
changes can be wrapped in a **transaction**: a promise that either all of them
happen, or none do.

**Options considered:** SQLite, Postgres, MongoDB, MySQL.

**Three concrete reasons Postgres wins here, each stated plainly and technically:**

1. **Real concurrency control** (directly required by §11 scenario 4, last-room
   contention).
   - *Plain:* when two people reach for the same last hotel room at the same
     instant, Postgres lets us guarantee only one of them actually gets it. SQLite
     would just lock the whole database file for that moment - it would look safe,
     but only by accident, not because the logic was built.
   - *Technical:* Postgres offers row-level locking (`SELECT ... FOR UPDATE`) and
     atomic conditional updates (`UPDATE ... WHERE rooms_left > 0`), so exactly one
     transaction wins a race on one specific row while unrelated transactions
     proceed unblocked. SQLite's locking is file/table-level - it serializes *all*
     writers globally rather than resolving row-level contention correctly.
2. **Real multi-table transactions** (so a booking can never end up half-saved).
   - *Plain:* one booking touches several things at once - the request, a hold, a
     price record, a booking attempt. Postgres can promise "either every one of
     these saves happens, or none do."
   - *Technical:* Postgres gives full ACID guarantees across multiple tables in one
     transaction. MongoDB's core guarantee has historically been per-document;
     multi-document transactions exist but are heavier and less idiomatic for a
     relational-shaped problem like this one.
3. **The data is naturally relational, with real constraints to enforce.**
   - *Plain:* our data is full of "this must belong to exactly one of that" rules -
     a hold belongs to one component, a request belongs to one user, a room can only
     be booked once. Postgres enforces these itself, so a bug in our code gets
     caught by the database, not shipped silently.
   - *Technical:* Postgres enforces foreign keys, unique constraints, and check
     constraints at the database layer, so invariants like §03's ownership scoping
     or "one confirmed booking per held component" hold even under an application
     bug. A schema-less store needs all of that reimplemented by hand in app logic.

MySQL was considered and is also relational/viable, but Postgres's richer
locking/constraint tooling (e.g. `SKIP LOCKED`) is the more common, better-documented
choice for a correctness-heavy system like this one, and free hosted tiers
(Render/Supabase/Neon) exist either way.

### Scheduler: APScheduler, in-process (re-confirmed)

No new reasoning beyond what's already logged above (Stack section) - still the
right call: zero extra infrastructure, runs inside the same FastAPI process, and the
brief's own scale target (100 requests, §12) doesn't demand Celery+Redis's
horizontal scalability. The Methodology Report will explicitly state this wouldn't
be the pick at real scale (1,000+ requests, §12's own forward-looking question) -
intellectual honesty about the limit, rather than over-building past what's tested.

### Frontend: React + Vite + TypeScript (settled, previously open)

- **React** - component-based UI library; matches §10's six required screens
  naturally as separate components; already the candidate's strongest frontend
  skill.
- **Vite** - build/dev tool; near-instant reload during development vs. older
  tooling (Create React App/Webpack); no meaningful downside at this project's size.
- **TypeScript** - static types over JavaScript; specifically valuable here because
  the system has many small, important state enums (`complete`/`provisional`/
  `unavailable`, hold `valid`/`expired`, booking `confirmed`/`partial`/`failed`) -
  TypeScript catches a frontend mishandling one of these at build time instead of
  live during a demo.

**Rejected, on record:** Next.js (SSR/routing conventions this project gets no
benefit from - no SEO/marketing surface); Vue/Svelte (viable, but a real
context-switch cost against already-decided React fluency, for no project-specific
benefit); plain JavaScript without TS (rejected specifically because of the
state-enum risk above).

## Simulation design: SimClock, SimController, and the Scenario Lab (2026-11-20)

This is the concrete design behind §11's "deterministic fixtures and controls" -
built incrementally, one version at a time, instead of all at once in V4.

- **`SimClock`** - every place in the code that needs the current time reads it from
  one shared clock object instead of calling the system clock directly. In real mode
  it just returns the actual time; in simulated mode something can **set** it to a
  specific moment or **advance** it by N minutes, and every hold/expiry/monitoring
  calculation reacts instantly - this is what makes a 2-minute hold or a 5-minute
  cycle demoable in seconds instead of by waiting.
- **`SimController`** - a set of levers that can, on command: force the next price
  for a specific component; force a component to fail/time out/return "unknown";
  force a room's inventory to zero; trigger a monitoring cycle immediately; reset
  everything back to a known seed state.
- **The Scenario Lab** - rather than hiding these levers as internal-only tooling,
  they're exposed as a real page at a real URL inside the running app (a `/lab`
  route), clearly visually separated from the real user-facing screens so it's never
  confused with the actual product, but reachable directly and instantly during the
  live demo/review (§13) without needing a separate tool or terminal session. This
  satisfies §11's "reviewers must be able to reset and replay each case" literally -
  the dials/toggles *are* the replay mechanism, not a description of one.

**Why built incrementally, one version at a time:** each version only gets the
levers it actually needs to demo and stress-test what it just built - V1 needs just
enough to show an alert firing; failure injection arrives with V2 (once there's a
booking flow to break); concurrency-triggering arrives with V3/V4 (once two
simultaneous users is a real scenario). This avoids building the full scenario
runner speculatively before there's anything real for it to control.

## Per-version stress-testing process (2026-11-20)

Once a version's features exist, it gets its own deliberate pass of trying to break
it, using whatever Scenario Lab levers exist at that point: firing the same
confirmation twice, forcing a failure right after a success, forcing a timeout then
reloading persisted state, and (once concurrency exists) firing two near-simultaneous
booking attempts at the same last room. Whatever breaks gets patched immediately, and
both the break and the fix are written into that version's doc
(`docs/versions/VX.md`) - this becomes real evidence for §14's Verification Package,
and doubles as rehearsal for §13's live "diagnose an unseen failure," since several
real failures will already have been caused and fixed by hand before that review ever
happens.

## Per-version documentation structure (2026-11-20)

One file per version, `docs/versions/V1.md`, `V2.md`, etc., same template each time
so versions are easy to compare later:

1. What this version does (plain English, a few sentences)
2. What's new since the last version
3. Architecture active this version (what's wired up vs. still stubbed)
4. Data sources used - field by field, what's real/sandbox vs. simulated
5. Simulation controls available this version (Scenario Lab levers that exist so far)
6. Stress tests run + results (what broke, what got patched, what's still a known gap)
7. Decisions made this version (pointers into this file, not duplicated)
8. Honest gaps - explicitly deferred to the next version, and why

This is designed to produce most of §14's Methodology Report and Data-source
Dossier content incrementally, as a byproduct of building, rather than as a
last-minute writing exercise.
