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
versions (V1-V4) instead of one flat plan - see `docs/internal/early-plan.md` for the full
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
and explicitly allows disclosed, honest gaps. `docs/internal/early-plan.md` exists to correct
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

## Second Hotelbeds account - fallback only, not a quota multiplier (2026-11-21)

After round 10's exploratory testing exhausted the free Hotelbeds key's 50/day
quota faster than expected, a second Hotelbeds evaluation account was registered.
**Decision: it is kept strictly as a fallback (e.g. if account #1 gets suspended
or is otherwise unusable), never run alongside account #1 to get ~100 real
calls/day in practice.**

**Why**: the assignment's own §04 explicitly states *"do not bypass
authentication, access controls or rate limits."* Hotelbeds set the 50/day cap
deliberately as an access control on its free evaluation tier; round-robining
between two accounts to double real daily throughput is functionally the same
thing that line is warning against, even though technically each account's own
individual limit is respected. This project has been consistent elsewhere about
not working around access controls for convenience (ruling out MakCorps/Apify-
style scraping, ruling out unofficial Skyscanner wrappers on the same grounds) -
treating a second account as an active multiplier here would be inconsistent
with that standard, and hard to defend if asked directly in the interview.

**Practical conclusion**: the original 50/day is enough once testing is
disciplined - cache the resolved destination code once, save real API responses
as local fixtures for UI/dev iteration, and only make genuinely new real calls
when something has actually changed (a fresh price check, a final pre-demo
verification). The second account's credentials are saved in `backend/.env`
(`HOTELBEDS_FALLBACK_*`) for the fallback case only.

## Pre-code gap check, and two schema/handling decisions before V1 (2026-11-21)

Before writing any backend code, re-checked the whole project (every doc +
the original assignment PDF, all 5 pages) against what was actually planned,
specifically because real external sources (Sabre, Hotelbeds) had since
replaced what `V1_MODULES.md` originally spec'd as all-simulated. Found and
fixed three real gaps, not cosmetic ones:

1. **`V1_MODULES.md` was stale** - rewritten so `sources/flights.py` and
   `sources/hotels.py` call the real, confirmed-working Sabre/Hotelbeds clients
   (new `sabre_client.py`/`hotelbeds_client.py` modules), not simulated logic.
2. **No raw-response/source-reference storage existed in the schema** - this
   silently dropped the earlier bronze/raw -> gold/normalized decision and
   would have left nothing for §14's data-source dossier "sample data" and
   field-mapping requirements. Added a `raw_sources` JSONB column to
   `price_observations`, populated by `pricing.py` from each real source
   module's full response.
3. **Hotelbeds' currency - decided properly, including a real functional
   conflict caught before it became a bug.** The first instinct was to mark the
   hotel component `provisional` (using the assignment's own §05 complete/
   provisional/unavailable vocabulary) until currency was confirmed. That
   would have meant a hotel-containing package could *never* be `complete`,
   since §05 says only complete packages can trigger a budget alert - silently
   breaking V1's entire reason for existing (proving one alert can fire end to
   end). Caught this before writing any code, not after debugging a demo that
   never alerts. **Resolution**: settled the currency question for real first
   - a `CheckRates` call (Hotelbeds' own documented next step after search,
   not a guessed parameter) explicitly returned `"currency": "EUR"`. V1 applies
   a documented, labeled EUR->INR conversion at a fixed rate, keeps the
   component `complete`, and reserves `provisional`/`unavailable` for genuine
   data gaps (an API call failing, returning nothing) - which is closer to
   what those statuses are meant to represent in the brief anyway.

**Also surfaced, not silently absorbed**: today (2026-11-21) is day 4 of the
7-day window (received 2026-11-18, due 2026-11-25) and no backend/frontend
code existed before this point - everything so far has been research and
planning. Decision: proceed with V1 now and reassess realistic scope after
V1/V2 land, rather than pre-emptively cutting V3/V4 before any code exists to
judge velocity against. `SIMPLE_PLAN.md` already treats V3/V4 ending up
"explained, not built" as an acceptable, honestly-labeled outcome - this isn't
a new risk, just a confirmed one.

## Pre-deploy hardening pass (2026-11-22)

A deliberate, adversarial review of every V1 file - "what would break later,
not just today" - before deploying. Nine real issues found and fixed, each
verified with a real test, not just read-through:

1. **`POST /book` had no idempotency guard.** A double-click, a retried
   request, or two open tabs would silently create two separate
   `BookingAttempt` rows for the same notification - directly contradicts the
   idempotency concept central to the 30%-weighted booking-correctness
   criterion. Fixed with both an application-level check (returns the
   existing booking instead of creating a new one) and a DB-level unique
   constraint on `notification_id` (the only thing actually atomic under two
   near-simultaneous requests) with `IntegrityError` handling for the race.
   **Verified**: booked the same notification three times through the real
   running app - same booking ID and supplier refs every time, one row in
   the database.
2. **The same race existed in notification creation**, just less obviously:
   two near-simultaneous "check price now" calls could both pass the
   `already_notified` check before either committed, creating two
   notifications - exactly what Sec. 07 explicitly forbids. Fixed with a
   transaction-scoped Postgres advisory lock keyed on `request_id` (doesn't
   block unrelated requests, releases automatically on commit). **Verified**:
   fired 15 concurrent real `check` calls against the same request - 16
   separate price observations were created (correct, each check is a real
   event), but exactly 1 notification (correct, matching V1's one-alert rule).
3. **Real supplier failures were being fully swallowed.** `sources/flights.py`
   and `sources/hotels.py` both caught `Exception` and returned
   `"unavailable"` without logging anything - a real Sabre/Hotelbeds outage
   during Sec. 13's live review would leave literally no diagnostic trail.
   Fixed with `logger.exception(...)` before the fallback return, and global
   logging configured in `main.py`. **Verified**: forced a real exception via
   a mocked client call and confirmed a full traceback now appears in the log.
4. **No caching meant every check cost real quota**, and the planned V2
   5-minute scheduler would have made this much worse (Hotelbeds' 50/day
   quota, confirmed scarce by exhausting it during research). Added a shared
   4-minute TTL cache (`ttl_cache.py`) in both supplier clients - absorbs
   rapid repeats without changing how often a *meaningfully new* real price
   gets fetched. **Verified**: a repeat check went from ~7.6s (real call) to
   ~0.03s (cache hit), same correct total.
5. **No rate-limiting on outbound Hotelbeds calls**, despite its documented
   8-requests-per-4-seconds burst limit - a burst of concurrent checks could
   get throttled by the real supplier, and that throttling would have been
   indistinguishable from "no hotels exist" once it hit the same swallowed-
   exception path as #3. Added a minimal thread-safe throttle (`rate_limit.py`).
6. **Sabre's token cache had no concurrency guard** - many requests hitting an
   expired token simultaneously could each independently fire a refresh
   (thundering herd). Added a lock with a re-check after acquiring it.
7. **No indexes on the foreign-key columns actually being queried.** Postgres
   auto-indexes primary keys, not foreign keys - `price_observations.request_id`
   (plus a composite index matching the real query shape: filter by
   `request_id`, order by `observed_at`), `notifications.request_id`, and
   `trip_requests.user_id` were all unindexed. Invisible today, would have
   become a real sequential-scan problem once the V2 scheduler starts
   appending rows for days.
8. **No production API base URL on the frontend.** `api.ts` called a relative
   `/api/...` path, which only resolves via Vite's dev-only proxy - a real
   split deploy (frontend and backend on separate hosted services) would have
   404'd every request. Added `VITE_API_BASE_URL`, read at build time,
   defaulting to empty (same-origin) for local dev. **Verified**: building
   with the env var set bakes the real backend URL into the bundle.
9. **Two frontend unhandled-promise-rejection gaps** (a failed `listUsers()`
   call left "Loading users..." shown forever with no error; a failed
   `listObservations()` call for one request silently vanished) - both now
   surface an actual error message instead of failing silently.

One more, caught by the frontend's own linter rather than by inspection: a
`ComponentRow` prop was named `ref`, shadowing React's own reserved prop name
of the same meaning - works today (a plain prop, not an actual DOM/component
ref), but a real footgun waiting to happen. Renamed to `supplierRef`.

**Deliberately not "fixed" here, and why**: `PriceObservation.raw_sources`
storing the full raw API response on every check will grow without bound
once the V2 scheduler runs for days, with no pruning policy anywhere in
V1-V4's plan. Not fixing this now, on purpose - an archival/retention policy
is a real design decision (keep N most recent? time-based? never prune and
just document the growth?) that deserves its own consideration when V2's
scheduler is actually built, not a reflexive fix bolted on today. Logged here
so it isn't forgotten, not silently deferred.

This pass doubles as real evidence for Sec. 14's Verification Package and
Sec. 11's "repeatable scenario" spirit (the concurrency tests above are
exactly that, just run manually rather than through the Scenario Lab yet) -
and is exactly the kind of stress-testing `DECISIONS.md`'s "Per-version
stress-testing process" entry describes, just applied before the deploy
milestone rather than strictly per-version.

## V1 deployed to Render (2026-11-21)

Deployed now, right after V1, rather than waiting until V3/V4 - reasoning
already logged in `SIMPLE_PLAN.md`/chat history: hosting-specific surprises
are safer to find with three days of runway than the night before the
deadline.

**Platform: Render**, all three pieces under one account - free Postgres, the
FastAPI backend as a web service, the Vite build as a static site. Matches the
already-decided "lightweight PaaS, no AWS" stack choice; one platform is
simplest to manage solo.

**Checked before committing, not assumed**: Render's free-tier limits, since
V4 eventually needs to run on whatever we pick today.
- Free web services spin down after 15 min idle (~30-60s cold start on
  wake) - and since V2's monitoring loop will be an in-process APScheduler,
  not a separate worker, **it stops ticking entirely while the service is
  asleep**. Documented as an honest hosting-tier limitation, not a bug - wake
  the service before any live demo/review.
- Free Postgres expires 30 days after creation (this one: 2026-12-21) - well
  past the 2026-11-25 deadline, irrelevant for submission, only matters if
  the link needs to stay live long after.
- 512MB RAM / 0.1 CPU - Sec. 12's 100-request load test runs against
  simulated suppliers per the brief's own wording (CPU-bound, not network-
  bound), so this is a real, honest data point worth reporting for that
  section rather than a blocker to route around.

**What the actual setup required** (`render.yaml` at the repo root defines
the intended shape; applying it needed real CLI/API work beyond what a
Blueprint alone does):
- Render's Blueprint `fromService` field only returns a private-network
  hostname, never a public HTTPS URL, and Blueprints don't support variable
  interpolation - confirmed directly against Render's own docs before
  assuming otherwise. `CORS_ORIGINS` (backend) and `VITE_API_BASE_URL`
  (frontend, baked into the JS bundle at build time) were set to real values
  via the API after both services existed and their real `onrender.com` URLs
  were known - each got a random suffix (e.g. `tavora-backend-fm0b`), not the
  plain service name, confirming it was right not to have hardcoded a guess.
- Render needs its GitHub App explicitly authorized for this specific
  private repo before it can deploy from it - a one-time action only
  possible from the GitHub/Render UI, done by the user mid-setup.
- Seeding the production database hit a real, still-unresolved external-
  connectivity issue (`psql`/`psycopg2` to the database's public hostname
  failed with "SSL connection has been closed unexpectedly" even with
  `sslmode=require`) - not chased further once a cleaner path existed:
  Render's free plan doesn't support one-off CLI jobs either (paid-only),
  so the seed script was temporarily chained into the backend's own
  `startCommand`, which uses the already-working internal network, then
  reverted once seeding was confirmed in the logs. A database-side setting
  change was considered as an alternative fix and deliberately skipped in
  favor of this safer option - the session's own auto-mode safeguard
  flagged that alternative as worth a second look, which matched this
  session's own judgment on it.

**Verified end to end against the real deployment**, not just "it deployed
without erroring": `/health` and `/api/users` against the real production
database, a real `check` call that hit real Sabre + real Hotelbeds from the
deployed backend (same ₹34,559.65 total as local testing), and a full real
headless-browser run against the live frontend URL - Dashboard → Notifications
→ Offer Review → Confirm booking → Booking Result, plus a direct navigation to
`/lab` to confirm the SPA rewrite rule works on a cold URL, not just
client-side navigation. Zero console errors.

**Open/unresolved**: why direct external Postgres connections failed - the
internal-network workaround makes this a non-blocker, but the root cause
(account-level restriction? a Render free-tier behavior not matching its own
general docs? something local to this network?) wasn't chased down, since a
clean alternative existed.

## V2 implementation (2026-11-21/22)

Built per the module plan already discussed in chat: a new `last_alerted_total`
column on `trip_requests` drives the real alert state machine
(`app/monitoring.py`), `held_observation_id`/`held_until` on `notifications`
drive the real 2-minute hold, `app/scheduler.py` runs the same check logic
automatically every 5 minutes, and `routers/booking.py` implements one real
failure scenario (a forced component failure triggers a compensating
cancellation of whatever already succeeded).

**The booking endpoint now derives the total from the held observation
server-side**, not from whatever the client sends - V1 trusted the client's
`accepted_total`; V2 looks up the actual held price itself. A real
correctness tightening, not just a V2 feature add.

**Only one of the six failure-table rows was built** (Sec. 09) - "one
component books, then another fails," chosen because it's the one that
actually exercises compensation logic, which generalizes to the other five.
Building all six wasn't the goal; building one correctly, with a real test
proving it, was.

**A real bug was found and fixed mid-build, not after**: every timestamp
this app returned (`created_at`, `reviewed_at`, `held_until`, etc.) was a
naive UTC value with no timezone marker. A real browser test (not curl, not
reading the code) showed a brand-new 2-minute hold rendering as already
expired - the browser (outside UTC) silently read the naive timestamp as
local time. Root-caused, not patched around: switched every `DateTime`
column to `DateTime(timezone=True)` and every clock read in the codebase
from `datetime.utcnow()` to `datetime.now(timezone.utc)`, re-verified in a
real browser afterward with a correct live countdown. This is exactly why
the project insists on real browser/API verification over reading code and
calling it done - this bug was invisible in every curl-based test run
before it.

## Full adversarial review pass, post-V2 (2026-11-22)

Went back through every file - V2's new code and a re-check of V1's - looking
specifically for "what's exploitable or will quietly break," not "does it
read fine." Found and fixed three real issues, each verified with a real
test:

1. **A real, significant authorization gap**: `check`, `review`, `book`,
   `observations`, and `get_booking` had **no ownership verification at
   all**. Any user who knew or guessed a request/notification/booking ID
   could check prices, review offers, and book on someone else's request -
   directly contradicting Sec. 03's explicit "requests, notifications and
   booking actions must remain scoped to their owner." This existed from V1
   and the earlier hardening pass missed it too - it's not a V2-only
   regression, it was always there. Fixed by adding a `user_id` parameter to
   every affected endpoint and a shared `app/ownership.py` helper (one
   implementation, used everywhere, rather than a copy-pasted filter per
   endpoint - which is exactly how this gap happened the first time).
   **Verified** with real cross-user attempts: User B attempting to check,
   review, book, or read User A's booking all correctly return 404 now;
   User A's own actions on their own data still work.
2. **The scheduler's per-request exception handler never rolled back the
   shared session.** All requests in one monitoring cycle share a single DB
   session; Postgres aborts a transaction on error until it's rolled back -
   so one request's DB-level failure would have silently poisoned every
   request checked after it in the same cycle, not just that one. Added
   `db.rollback()` to the except block.
3. **No pinned dependency versions for the backend** - Sec. 14 explicitly
   asks for a dependency lockfile; `requirements.txt` had none. Pinned every
   direct and transitive dependency to an exact version (frontend already
   had `package-lock.json`, a real lockfile - backend didn't have an
   equivalent). **Verified** by installing from the pinned file into a
   completely fresh virtualenv and confirming the app still imports cleanly.

**Also improved, not a bug but a real gap**: the offer-review countdown was
computed purely from the browser's wall clock, so a Scenario Lab clock
advance that happened *before* the page loaded wouldn't be reflected in the
displayed countdown until the user tried to book and hit the server's real
rejection. Fixed by having the page also fetch the server's current sim time
and correct for the offset - the display now matches what the server will
actually enforce.

**Noted, not fixed, and why**: the Scenario Lab's own endpoints
(`/api/lab/*`) still have no ownership gating - any user could override
prices or arm a booking failure for any request_id. Left as-is deliberately:
the Lab is explicitly dev/demo-only tooling, never shown on or reachable
from the real traveller-facing screens, and gating it would be solving a
problem the brief doesn't ask about for internal tooling that isn't part of
the shipped product.

## V3 implementation (2026-11-22)

Built per the module plan discussed in chat: Users B and C seeded with their
real Sec. 02 requests, edit/pause/cancel/reactivate on `TripRequest`, a real
pytest suite, and the operations view.

**Edit invalidation, the exact mechanism**: rather than inventing a new
"stale" state, editing a request clears any un-booked notification's
`held_observation_id`/`held_until` and resets `last_alerted_total` - a
booking attempt against the old offer then hits the identical "no active
hold, review again" rejection V2 already built. Reusing an existing,
already-tested rejection path instead of adding a new one.

**The operations view is a required product screen, not Lab tooling** -
caught this distinction late (Sec. 10 lists it among the six required
screens) and corrected course: `/api/ops/*` is scoped per user like every
other real screen, with no special "admin" concept anywhere else in this
app to justify making it global.

**Two real, previously-open items got settled as a byproduct of seeding
Users B and C for the first time, not through dedicated research**: Jaipur's
hardcoded Hotelbeds coordinates (hardcoded since round 11, never
independently verified) turned out correct, confirmed by User C's first
real check; and User B's 4-adult/2-room request confirmed the occupancy
math is genuinely correct by inspecting Hotelbeds' raw response directly
(it explicitly tags the matching rate `"rooms": 2, "adults": 4`), not just
trusting the extracted total looked plausible.

**The test suite deliberately covers three things, not everything** -
pricing math, the alert state machine, and ownership scoping - because
those are explicitly the three `SIMPLE_PLAN.md` called out as "most likely
to silently break." Not a from-scratch attempt at full coverage; a targeted
one matching the brief's own risk assessment. Runs against a dedicated test
database (`tavora_test`), never the dev/prod one, with every test starting
from a completely empty schema so no test can pass because an earlier one
happened to set something up first.

## V4 implementation (2026-11-22)

Closes out the three honest gaps V3 carried forward: the remaining five of
six Sec. 09 failure-table rows, Sec. 11 scenario 6 (timeout + restart), and
Sec. 12's 100-request load demonstration.

**Zero schema changes - deliberate.** Every new behavior is expressed with
new *string values* in the existing `flight_status`/`hotel_status`/
`cab_status`/`aggregate_status` columns (`"unknown"`, `"cancellation_failed"`,
`"needs_reconciliation"`, `"manual_intervention"`, `"in_progress"`), not new
columns. V2's schema change meant a real production DB reset; this time the
same breadth was reachable without touching the deployed database's schema
at all, so the deployed DB wasn't touched for this version.

**"Repeated confirmation or job delivery" (row 1)**: already covered since
V1/V2 (idempotency check + DB unique constraint on `notification_id`) -
re-verified, not re-built, now with its own test
(`test_double_booking_the_same_notification_is_idempotent`).

**"Inventory disappears or hold expires" (row 2)**: hold expiry was already
built in V2 (`held_until` check in `book()`). The other half - inventory
disappearing *during* booking despite a valid hold - is new: a forced
`"unavailable"` outcome (Scenario Lab) stops the booking loop at that
component and compensates everything confirmed before it, same shape as a
direct failure but a distinct status so "requote needed" is visible, not
indistinguishable from a supplier error.

**"One component fails after another books" (row 3)**: unchanged from V2 -
already the one scenario built there.

**"Supplier books but its response times out" (row 4)**: new. A forced
`"timeout"` outcome leaves that component `"unknown"` and the whole booking
`"needs_reconciliation"` - `book()` refuses to start a second attempt on
that notification (returns the same stuck row), and only the new
`POST /api/bookings/{id}/reconcile` endpoint can resolve it, in either
direction (it was actually booked / it never was). This is the literal
"resolve the unknown outcome before creating another booking" requirement,
not a looser approximation of it.

**"Application restarts during booking" (row 5) / Sec. 11 scenario 6**: the
real mechanism is that `book()` now inserts the `BookingAttempt` row
immediately (all components `"pending"`, aggregate `"in_progress"`) and
commits after *every single component*, not once at the end. A forced
`restart_after` Scenario Lab lever stops processing right after a given
component commits, simulating a crash there. A later `book()` call on the
same notification finds the `"in_progress"` row and resumes from the first
still-`"pending"` component - never re-decides the outcome of something
already committed, never creates a second row. Verified live against the
real running local server (not just pytest): booking stopped after
`flight` confirmed, a second call to the same endpoint resumed and finished
`hotel`/`cab` without a duplicate `BookingAttempt` row.

**"Cancellation fails" (row 6)**: a forced `cancel_failure` Scenario Lab
lever makes a specific component's compensating cancellation itself fail -
that component becomes `"cancellation_failed"` (its supplier ref is kept,
never erased) and the aggregate becomes `"manual_intervention"`, distinct
from `"partial"` so a stuck booking that falsely claims a completed rollback
never looks identical to one that correctly recovered.

**100-request load demonstration (Sec. 12)**: `backend/scripts/load_test.py`
seeds 100 active requests on a dedicated, throwaway `tavora_load_test`
database (never dev/prod) and runs the real, unmodified `run_one_cycle()`
three times, with `app.monitoring.build_package` patched to a deterministic
simulated supplier - the same patch point every pricing/alert unit test in
this repo already uses, not a separate load-test-only code path. No real
Sabre/Hotelbeds/cab calls are made, per the assignment's own "do not
generate unnecessary load against real services." Real captured numbers
from an actual run: 3 cycles of 100 requests each, ~0.7s/cycle (~7ms/
request), 0 errors, 0 duplicate alerts, 40 real notifications created
(matching the deterministic fixture's expected alerting population
exactly), 0 unfinished work. Full report and the 1,000-request extrapolation
in `docs/VERIFICATION_PACKAGE.md` §3.

**Not done, and still deliberately last**: visual polish (Sec. 10/15's own
stated lowest priority, unchanged since V1).

## Request-input validation fix (2026-11-22)

Found live, not in review: creating a request with the return date on or
before the outbound date (e.g. outbound 2027-03-05, return 2026-12-04), 9
adults, 9 rooms produced a real, nonsensical priced package - flight and
cabs happily returned prices for a trip that never happens, while hotel
correctly came back `unavailable`. Nothing had ever checked that the dates
made sense, in either direction.

**Fix**: `app/validation.py::validate_date_order`, called at request
creation, request edit (against the *merged* outbound/return values, not
just the two fields in isolation), and inside
`app/monitoring.py::create_observation` - the one real choke point both the
manual "check price now" button and the automatic scheduler go through, so
a request that became invalid before this validation existed is also
blocked from ever being priced again, without spending a real supplier
call. Also added basic Pydantic field bounds (adults/rooms ≥ 1, budget > 0,
star rating 0-5) that were previously unconstrained. Five new tests in
`backend/tests/test_validation.py`, including one that reproduces the
already-broken request directly (bypassing the API, same as data that
predates this fix).

**The honest lesson, not just the fix**: this kind of basic input
validation should have been built alongside each feature from V1 onward,
not left until someone manually tried to break it. Recorded as a standing
practice for any UI/input work from here on, not just this one case.

## Product-framing discussion and the UI pass plan (2026-11-22)

A real, substantive question was raised after V4 shipped: does the brief
ask for "a general booking website AND a separate simulation," and does the
current build read as "just a simulation" rather than that? Checked against
the brief's own §01/§03 wording (quoted in full in `docs/internal/ui-plan.md`) - it
asks for one real product whose booking *action* is simulated, not two
separate things. Agreed as the correct reading.

A specific UI concept was then floated - a locked, non-interactive "replay"
mode (click through pages exactly like watching someone else's real
booking on their PC, pre-selected and unchangeable) with a "Custom/
Simulation" toggle into the real interactive product. **Decided against it**
in favor of a lighter approach: keep one real interactive product, polish
its pages to look and flow like a real booking site, and get the "watching
someone's real booking" effect for free from the existing mock-user
switcher landing on A/B/C's real seeded data - no separate viewer
architecture needed. Full reasoning in `docs/internal/ui-plan.md`, which is now the
living tracker for this not-yet-started pass (status, open items, and
where the decision record lives), kept separate from this log so the two
don't have to be cross-referenced to find either.

**No UI implementation has started as of this entry.** Standing
instruction: wait for the candidate's own batched list of UI changes
(expected after their own review, through Monday night) before building
anything in this area.

## Real frontend reference survey (2026-11-23)

Still no UI implementation - this was explicitly research, requested
directly: "go through various websites and see their frontend so that we
can have ours like that too." Took real, live headless-browser screenshots
(not descriptions from memory or training data) of Tavora's own real site,
Google Flights, and Booking.com; ixigo/Goibibo/MakeMyTrip were blocked by
rate-limiting or anti-automation and skipped rather than guessed at.
Screenshots live in `docs/ui_references/`; the per-site observations and
what each pattern maps to on our own pages are in `docs/internal/ui-plan.md`'s new
"Real frontend reference survey" section - most notably, Tavora's own real
trip-wizard page (a numbered step tracker + a sticky summary-card-with-CTA)
is the single most directly transferable reference found, since our
Request Form / Offer Review / Dashboard are conceptually the same shape
that page already is.

## UI pass implementation (2026-11-23) - V5

Requested directly: "go ahead and start implementing every change that we
talked about before and the ui changes fully" - before the candidate's own
review pass, so this was built from the plan already on record (the
lighter approach decided on above, and the reference survey's concrete
patterns) rather than a separate itemized list. Full record in
`docs/versions/V5.md`; summarized here:

- A real design system (CSS custom-property tokens - color, spacing,
  radius, shadow), Inter typeface, consistent pill buttons/cards/status
  badges everywhere, replacing one-off ad hoc styling.
- Request Form restructured into three grouped sections plus a sticky
  "Trip summary" card carrying the submit action - Google Flights'
  grouped-search-card pattern and Tavora's own sticky-summary-with-CTA
  pattern, applied together.
- Offer Review restructured the same way: itemized total on the left, a
  sticky offer summary (countdown + Confirm action) on the right.
- Scenario Lab copy fully rewritten (resolves the "worded weirdly"
  feedback) and consolidated to one shared target-request field.
- **Two real bugs found and fixed during this pass, not by code review but
  by actually looking at rendered screenshots**: a CSS specificity bug
  where two grid layouts were silently overridden by a same-element class
  defined later in the stylesheet (fixed by combining selectors instead of
  relying on source order); and a mobile viewport (390px) where the header
  had no responsive behavior at all and overflowed horizontally (fixed
  with a wrap breakpoint). Neither would have been caught without a real
  screenshot pass - the same lesson as this project's standing
  validate-proactively practice, just applied to layout instead of input
  handling: visual/layout correctness needs the same "verify against the
  real running thing" discipline as backend correctness, not just "the
  build succeeded."
- A full real flow (create → check → review → confirm) was exercised
  through the new UI end to end, screenshotted at each step, not just
  reviewed as static pages.
- No new frontend dependency was added to achieve any of this - plain CSS
  plus one Google Fonts link.

## Homepage, trip story, and color scheme (2026-11-23) - V6

Direct feedback after reviewing V5 live: "all the totals are unavailable"
(investigated first, before anything else - see below) and "this just
feels like a calculator, not a travel website" - specifically asking for a
homepage, a visible storyline of what each mock user "picked" among real
alternatives, no stock photos (emoji/simple marks instead), and a real
color scheme. Full record in `docs/versions/V6.md`; decisions worth
keeping here:

**The "totals are unavailable" report was investigated live, not assumed
to be a UI bug.** Confirmed real: User B's request (4 adults, 2 rooms) had
genuinely gotten `hotel_status: "unavailable"` from Hotelbeds repeatedly
since 2026-11-21. Re-running the exact same check live, twice, both
succeeded with real complete totals. Conclusion: this is the free
Hotelbeds sandbox's documented scarcity (50 req/day, limited test
inventory for a harder 2-room occupancy) actually manifesting, not a
regression from the V5 redesign (confirmed no backend code changed in
that version) and not the frontend misrepresenting backend data (the
backend's own stored history showed the same `unavailable` independent of
any UI). Also live-verified notifications still work correctly end to end
(forced a real alert, confirmed correct per-user scoping) before
responding, rather than asserting it from memory.

**Chose to surface real alternative data already being fetched, not
fabricate new content.** The user was explicit that stock photos weren't
wanted and weren't necessary - emoji or simple marks were enough. The
chosen implementation goes a step further than decoration: `PriceObservation.raw_sources`
already stores the *entire* raw Sabre/Hotelbeds response on every check
(up to 12 real flight itineraries, up to 9 real hotels, confirmed by
inspecting a real stored response directly) - only the single cheapest
eligible one of each was ever shown. `app/story.py` reads that already-paid-for
data and surfaces the rest, marking whichever one matches the
price actually used as "Picked." This makes **zero new real supplier
calls** - the "storyline" the user asked for is assembled from data the
system already has, which is both cheaper and more honest than inventing
placeholder options would have been.

**The homepage replaces nothing, it adds an entry point.** `/` is now a
real landing page (product intro + a profile card per mock user with
their real requests); the existing Dashboard moved to `/dashboard` rather
than being removed or duplicated.

**Color scheme**: one warm accent token (`#d9622b`) swapped in for what
was previously pure black, applied through the existing design-token
system from V5 - confirms that system was built generally enough to
absorb this kind of change without touching more than `:root`.

## V7 implementation (2026-11-24) - audit fixes, real migrations, CI, one real gap closed

Requested directly: "go ahead and fix everything you found" (the 11-finding
audit), "make a ci/cd and the automated tests before that" (real since
`Base.metadata.create_all` was the only schema-management path that ever
existed - no Alembic), and "go through the requirements... make sure we
have done all that." Full record in `docs/versions/V7.md`; decisions worth
keeping here:

**Real Alembic migrations added, not just schema-change-avoidance
continued.** V2 through V6 deliberately avoided schema changes specifically
*because* there was no real migration tooling - every prior schema change
either meant a production reset (V2) or was designed around to avoid one
entirely (V4-V6, explicitly documented as deliberate). Sec. 14 lists
"schema/migrations" as a required deliverable item; this was a real,
previously-unflagged gap. Fixed properly rather than worked around again:
`backend/alembic/`, a baseline migration generated against a genuinely
*empty* database (not the populated dev DB, which would silently produce
an empty no-op migration - caught and redone), stamped onto the existing
dev/prod schema without re-running it. `scripts/seed.py`/`reset.py` now
run real migrations; `reset.py` needed its own fix alongside this -
`Base.metadata.drop_all` never touched Alembic's own tracking table, which
would have made the post-reset `alembic upgrade head` think there was
nothing to do.

**Fixed all 11 audit findings, each live-verified before and after, not
just unit-tested.** The two Critical ones: a cancelled/paused request could
still be reviewed and fully booked (reproduced live, start to finish,
before fixing); a Scenario Lab price override didn't actually make a demo
deterministic, since the real supplier call still happened underneath and
could silently discard the override on failure - fixed by skipping the
real call entirely once an override is set, which also makes the Lab's own
description of itself finally accurate. Full list and fixes in
`docs/internal/audit-log-2026-11-23.md`'s updated findings.

**A fresh pass re-checking requirements against real code (not against
what `docs/VERIFICATION_PACKAGE.md` already claimed) found a real,
previously unflagged gap**: Sec. 06's "lowest observed valid total" and a
price-history chart were never built - only the single latest observation
was ever fetched anywhere in the frontend, despite the verification
document marking Sec. 06 "Done." This is exactly the risk of trusting a
status document instead of the real code, which is why this pass checked
the code directly rather than re-reading the checklist. Fixed: the
Dashboard now keeps a request's full history and shows latest valid total,
lowest observed valid total, and a real inline SVG chart (budget line
included) - no new charting dependency, reading data the backend already
returned from day one.

**CI added** (`.github/workflows/ci.yml`): backend tests against a real
Postgres service container, plus a dedicated step that drops and recreates
the schema and runs `alembic upgrade head` against it - catching the model
definitions and the migrations drifting apart, which `tests/conftest.py`'s
own `create_all`-based fixture (kept for per-test speed) can't catch by
itself. Frontend job runs the same `npm ci && npm run build` a contributor
would run locally.

## Production deploy of V7's migrations - two real failures, both fixed live (2026-11-24)

Worth recording honestly, not glossed over: deploying V7 to production broke
the live site for a few minutes, twice, before it was right.

1. Configured Render's `preDeployCommand: alembic upgrade head` first - the
   documented-for-this-purpose mechanism. The deploy "succeeded" but
   `GET /api/requests` immediately started returning 500s in production:
   `column trip_requests.updated_at does not exist`. The deploy log showed
   why: `"Predeploy command not run. Commands can only run on paid instance
   types"` - a free-tier limitation, confirmed only by watching a real
   deploy fail, not documented anywhere obvious beforehand. Fixed by
   chaining the migration into `startCommand` instead (the same pattern
   already used for one-off scripts on this project, since the free plan
   also has no job-running support).
2. Second deploy with that fix also failed: `psycopg2.errors.DuplicateTable:
   relation "users" already exists`. Production's five tables were created
   back in V1 via `Base.metadata.create_all`, long before Alembic existed in
   this project - they were never "stamped" at the baseline revision, so
   Alembic had no record of them and tried to `CREATE TABLE` from scratch,
   colliding with real data. Fixed with
   `alembic stamp ba68ff3cc834 && alembic upgrade head && uvicorn ...` for
   one deploy (stamp first, matching exactly what local dev's database
   needed too - see the "baseline" migration's own commit), confirmed via
   a real request that the new column was there and the app worked, then
   reverted `startCommand` to the permanent, simpler
   `alembic upgrade head && uvicorn ...` (no stamp needed going forward,
   since production's `alembic_version` table now genuinely exists).

**Separately, requested directly afterward**: a full production data reset
(`scripts/reset.py`, chained into `startCommand` for one deploy, then
reverted) to clear a week of real test-session fingerprints before the
candidate's own review - a stray test notification, an edited demo request,
a jagged price-history chart built from dozens of real test checks. Verified
clean afterward: exactly users/requests 1, 2, 3, no notifications, matching
Sec. 02 exactly. `render.yaml` updated to match the final, real, live
configuration - including documenting the free-tier `preDeployCommand`
limitation directly in the file, not just here, so it isn't rediscovered the
hard way again if this project is ever recreated from scratch.

## Why monitoring needed a price-mutation layer (2026-11-24)

A real problem surfaced from the candidate's own review, not from code reading: Sabre's sandbox fares
never change call to call (a documented property of its test cell), a one-time hotel pre-fetch is by
definition a snapshot, and the original cab formula was a single fixed number. None of these move on
their own - which meant the entire "keep checking, alert on a drop" loop (Sec. 06/07) had nothing real
to actually demonstrate in default usage. Repeating a check would return the exact same total forever,
making the single most important scenario (price drop -> alert -> book) impossible to show without
manually touching the Scenario Lab every time.

Fixed with `app/price_mutation.py::mutate_all_prices()` - a small, bounded random nudge (±4% per call,
clamped to within ±30% of each row's own real/generated base value, verified to hold even after 200
repeated calls) applied to every synthetic flight/cab price and the cached hotel price. Wired into
`scheduler.py::run_one_cycle()` so it runs automatically once per real 5-minute cycle - ordinary usage
drifts on its own, no manual intervention needed - plus a separate `POST /api/lab/mutate-prices` for
on-demand nudging during a live demo session, kept distinct from `trigger-cycle` (which mutates and
checks/alerts in one step) so a presenter can nudge a few times first and only then trigger a check.

Considered and rejected: re-randomizing prices completely on each call (would break the "same base,
believable drift" property and could produce unrealistic swings); mutating only at request-check time
rather than once per cycle (would make the mutation's timing implicit and harder to reason about
separately from the check itself).

## The hotel occupancy-payload bug, found while building the real hotel cache (2026-11-24)

Investigating a real problem (User B's 2-room/4-adult hotel search appeared to only have 5 expensive
real options, nearly 1.5x her whole budget before flights/cabs) surfaced a genuine bug, not a data
scarcity problem: Hotelbeds' `occupancies` field needs one entry *per room* (each with its own adults
count), not one combined entry with `rooms` as a multiplier. The combined shape (what the code had
always sent) returned only 5 priced hotels for that exact search; the corrected split-occupancy shape
returned 47, confirmed via a real side-by-side live test before touching any code. Each rate line is
genuinely per-room (confirmed via its own embedded `"rooms":1` field), so multiplying the per-room rate
by the real room count is correct once the request itself is shaped right - the earlier audit finding
that called this "a missing room-count multiplication" was itself wrong; the real fix was the request
shape, not the arithmetic. Fixed in `app/hotelbeds_client.py` and `app/sources/hotels.py`; User B's
hotel total went from a budget-breaking ₹97,535 to a real ₹11,850 for 2 rooms.

## Introducing synthetic flight/cab directories alongside the real integrations (2026-11-24)

Direct instruction from the candidate, given explicitly as a priority call: keep Sabre's real
integration in the codebase and documented as proof of real, working access, but have the *live
product* read from generated synthetic directories for flights and cabs instead, since neither category
can demonstrate real price movement on its own (Sabre's frozen test-cell fares; no real cab-fare source
exists at all, already documented). Real-feeling, not real: same real route/airport/carrier shape Sabre
and India's actual domestic carriers provide, deterministically generated (seeded by route+date, so
regenerating is replayable, not random noise), clearly labeled synthetic everywhere it's shown. Hotels
stayed on a real, pre-fetched path instead (§ above) since Hotelbeds' real inventory turned out to be
usable once the occupancy bug was fixed - there was no need to abandon real data there.
