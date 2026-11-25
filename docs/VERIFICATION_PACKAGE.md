# Verification Package

*Automated test results, deterministic scenario fixtures and replay
commands, performance evidence, and a requirement-by-requirement checklist
against the assignment's own §01–15.*

## 1. Automated tests

**Run command** (from `backend/`, with a running Postgres and
`tavora_test` database - see `backend/README.md` "Running the tests"):
```
.venv/bin/python -m pytest -q
```

**Actual output, this run (2026-11-25, after the buy-now/shock-slider/Simulation-redesign round):**
```
...........................................................................
....................                                                [100%]
91 passed, 1 warning in ~12s
```
(The one warning is an unrelated upstream deprecation notice from `starlette.testclient`, not a defect here.)

**What's covered and why, by file:**

| File | Tests | Covers (from §12's list) |
|---|---|---|
| `tests/test_pricing.py` | 4 | Total-price calculation; itemization math across all three components; a Simulation override skips the real supplier call entirely, not just substituting the price after the fact |
| `tests/test_monitoring.py` | 7 | Alert rules: first-crossing, no-repeat-under-5%, re-alert-at-5%-further-drop, silent reset above budget, failed-check-does-nothing, deduplication |
| `tests/test_ownership.py` | 7 | User ownership scoping across check/review/book/observations/edit |
| `tests/test_booking.py` | 10 | Idempotent duplicate confirmation; hold expiry; forced `unavailable`/`timeout` outcomes; reconciliation (both directions); simulated-restart resume; cancellation failure |
| `tests/test_validation.py` | 5 | Request-input validation: reversed/equal date order rejected on create, edit, and check; zero adults/rooms rejected; an already-invalid pre-existing request is also blocked |
| `tests/test_story.py` | 7 | Legacy `/story` candidate extraction: cheapest-first sorting, non-INR fares ignored, missing/empty raw data handled, capped at 5, EUR→INR conversion, minimum star rating filter |
| `tests/test_request_status.py` | 8 | A paused/cancelled request can't be reviewed, booked (even with a pre-existing hold), or edited; cancelling clears an existing hold; cancelled requests' notifications aren't listed; editing bumps `updated_at`; a cancelled request can be restored from Trash and edited again afterward |
| `tests/test_occupancy_validation.py` | 3 | Rooms can't exceed adults, on create and edit (the real Hotelbeds-rejection bug this guards against) |
| `tests/test_distinct_places_validation.py` | 3 | Origin and destination can't be the same place, on create and edit, case-insensitively |
| `tests/test_reset_to_default.py` | 5 | "Return to default" restores a drifted demo request's seeded values exactly |
| `tests/test_simulation_log.py` | 4 | Every Simulation lever and real monitoring/booking event writes a real, queryable activity-log row |
| `tests/test_shared_room_scenario.py` | 2 | The shared-room race: one of two competing requests gets the room, the other gets a real `unavailable` |
| `tests/test_trip_directory.py` | 2 | `/directory`'s live candidate lists (what "Your Bookings" reads) match what `pricing.py` would actually pick |
| `tests/test_cab_and_flight_directories.py` | 8 | Cab/flight directory candidate lists: capacity/baggage eligibility filtering, cheapest-first ordering, distance/per-km fields present and consistent |
| `tests/test_price_mutation.py` | 3 | Market drift moves every option in the same route/search-key group by one shared step (not independently); the Simulation shock slider moves only the one trip's own market, by an exact signed amount |
| `tests/test_buy_now_and_shock.py` | 5 | Direct "buy now" (no notification click required) is ownership-scoped and rejects an incomplete check; shock-and-check is ownership-scoped and clamps an out-of-range fraction |
| `tests/test_lab_book_now.py` | 3 | Simulation's "book now" checks and books in one call, including enacting a scheduled failure immediately; rejects an incomplete check |
| `tests/test_review_notification.py` | 1 | Reviewing a notification actually returns a valid response (regression test for a real production 500) |
| `tests/test_sim_clock.py` | 2 | The simulated clock advances from a moving offset, not a frozen timestamp (regression test for a real production bug) |

**Fixture design**: `tests/conftest.py`'s `fresh_database` fixture drops and recreates the schema before every test, not just once per suite (verified idempotent by running twice). `TestClient` deliberately isn't used as a context manager, so the real APScheduler never starts during tests.

**Not automated, and why**: occupancy/date constraints, concurrent holds, expiry, duplicate confirmation, and recovery are exercised live (§2) instead - they need a real running server, real clock control, and (in one case) two concurrent HTTP requests, which is more reliable to verify by direct observation than to simulate in pytest.

**CI** (`.github/workflows/ci.yml`, runs on every push/PR to `main`):
- Backend: real Postgres service container, `pytest -q`, then a dedicated step that drops/recreates the schema and runs `alembic upgrade head` - the one place the real migration path gets exercised automatically.
- Frontend: `npm ci && npm run build` - the same commands a contributor runs locally.
- Found and fixed one real bug in the migration-verification step itself: `psql` didn't understand the `postgresql+psycopg2://` driver suffix, so it silently failed every run without affecting the actual test suite. Green on `main` now.

## 2. Deterministic scenario fixtures and replay commands

All seven of §11's required scenarios replay via **Simulation** (`/lab` page, `/api/lab/*` endpoints) - no waiting on real market movement, and always against a dedicated "Scenario" user, never A/B/C's own data. Replace the base URL below with `http://localhost:8000` for local replay. Shorthand in the table below drops the shared `/api/requests/{id}/` and `/api/` prefixes and the leading `POST`.

| # | Scenario | Replay command(s) | What it establishes |
|---|---|---|---|
| 1 | Below-budget trip | `check` → `review` → `book` (body `{"notification_id": N}`), all `user_id={A}` | Only A sees A's notification; booking returns real supplier refs at the exact held total |
| 2 | Price changes before review | `lab/override` (lower price) → `lab/trigger-cycle` → `review` - compare `original_observation.total_price` vs `current_observation.total_price` | The old notification's price is never trusted; review shows both, distinctly |
| 3 | Hold validity and expiry | `lab/clock/advance` (+3 min) after a review, then `book` | Booking after `held_until` passes is rejected with a specific error, never silently accepted |
| 4 | Last room contention | `lab/shared-room-scenario` (2 requests, 1 room) → `book` both | Only one claims the room (atomic `UPDATE ... WHERE rooms_remaining > 0`); the other gets a real `unavailable`, not a race |
| 5 | Partial booking failure | `lab/fail-component` (hotel, `fail`) → `book` | `aggregate_status = "partial"`: flight `cancelled` (compensated), hotel `failed`, cab `pending` |
| 6 | Timeout and restart | `lab/fail-component` (hotel, `timeout`) → `book` (→ `needs_reconciliation`) → `book` again (same stuck row, no dupe) → `reconcile` | An unresolved outcome is never guessed at or duplicated - `book()` refuses a second attempt until reconciled |
| 7 | Monitoring reliability | `lab/trigger-cycle` ×3 with no price change | No duplicate notification on repeat ticks - confirmed by tests, live runs, and the load test (§3) finding 0 duplicates |

Two more levers cover the rest of Sec. 09's failure table beyond §11's seven named scenarios:
- `lab/restart-after` (component: flight) - stops right after that component commits, as if the process crashed; a later `book()` resumes instead of duplicating.
- `lab/cancel-failure` (component: flight) - the next compensating cancellation fails, producing `manual_intervention` with the supplier ref preserved, not erased.

Prices only actually move every 4th `trigger-cycle` call (deliberate pacing, not flakiness) - call it a few times to see scenario 7's price change.

Simulation's endpoints are intentionally never ownership-gated - they're reviewer/demo tooling, not product surface, called out so it isn't mistaken for a security gap.

## 3. Performance evidence

**§12's reproducible 100-request load demonstration - run, not estimated.**

Run command (from `backend/`, against a dedicated, throwaway
`tavora_load_test` database - never dev/prod):
```
createdb tavora_load_test   # once
.venv/bin/python scripts/load_test.py
```

**Actual output, this run (2026-11-25, re-run fresh after the buy-now/
shock-slider round - the simulated-supplier mock's signature had drifted
one positional argument behind the real `build_package(trip_request, db)`
call and was failing silently per-request; fixed in
`scripts/load_test.py` and re-verified against a clean run):**
```
Environment: dedicated database 'tavora_load_test' (DATABASE_URL overridden above),
             100 active requests, 3 monitoring cycles,
             pricing patched to a deterministic simulated supplier (no real Sabre/
             Hotelbeds/cab calls made).

Cycle 1: checked 100 requests in 1.151s
Cycle 2: checked 100 requests in 0.938s
Cycle 3: checked 100 requests in 0.678s

--- Report ---
Supplier calls (simulated): 300
Cycle durations (s): [1.151, 0.938, 0.678]
Average cycle duration: 0.922s (9.2ms/request)
Errors (requests not checked in a cycle): 0
Total notifications created: 40
Requests with duplicate alerts (notification count > 1 for a constant price): 0 []
Unfinished work: 0 (every cycle checked all 100 requests)

Estimated cycle duration at 1,000 requests (linear extrapolation): 9.22s
```

**Not a shortcut**: `scripts/load_test.py` runs the real, unmodified `run_one_cycle()` - what the live scheduler and "Run cycle now" both call - patching only `app.monitoring.build_package` (the same point every pricing/alert unit test patches) with a deterministic mock: 10% of requests fail transiently, the rest split evenly under/over budget by request ID. Zero real Sabre/Hotelbeds/cab calls made.

**40 notifications is the verified-correct number**: 10 of 100 requests simulate a failure (never alert); of the other 90, the 45 even-numbered ones sit under budget and should alert once each; minus the 5 that are also divisible by 10 = 40. Matches exactly - no false alerts, no missed ones, across 3 cycles.

**At 1,000 active requests:**
- Compute isn't the bottleneck - this test's ~7ms/request extrapolates to ~7.3s/cycle, well inside the 5-minute interval.
- **Hotelbeds' 50-requests/day free quota is the real ceiling.** At that scale the architecture needs a shared cache keyed by destination+dates (not per-request), a paid tier, or both - cost is dominated by that tier, not infrastructure.
- The TTL cache and rate limiter are per-process memory, not shared - fine today, would need Redis the moment a second worker process exists.

## 4. Requirement-to-implementation checklist (§01–15)

| § | Requirement | Status |
|---|---|---|
| 01 | Objective: watch, notify, review, approve simulated booking | **Done** |
| 02 | Three mock users seeded with exact specified requests | **Done** - `backend/scripts/seed.py`; dates 2026-12-26+. A 4th "Scenario" user is also seeded, for Simulation to use instead of touching A/B/C |
| 03 | Request CRUD, INR/adults-only, ownership scoping, pause/cancel, edit invalidates offers | **Done** - pause/cancel invalidate stale offers too; a cancelled request can't be edited, reviewed, or booked |
| 04 | Independent source research, real/sandbox retrieval, labeled synthetic fallback | **Done** - `docs/DATA_SOURCES.md` |
| 05 | Itemized, feasible packages; no silent zeros; status labelling; freshness policy | **Mostly done** - `complete`/`unavailable` fully enforced; `provisional` is schema-forward only, no real path produces it yet (labeled gap) |
| 06 | 5-min scheduler + manual check; audit trail; latest/lowest valid total; price-history chart | **Done** - Dashboard shows all three, reading history the backend always stored |
| 07 | Real alert state machine (first-crossing, ≥5% re-alert, reset, dedup) | **Done**, test-covered; notification itself now carries itinerary/total/quote status |
| 08 | Fresh revalidation on review, explicit consent, real 2-minute hold, preserved through expiry | **Done** - one documented simplification: one shared package-level hold, not independently-tracked per-component expiries (see Methodology §8) |
| 09 | Component statuses, aggregate status, idempotent booking, failure-table behaviors | **Done, all 6 rows**: idempotent retries, inventory/hold-expiry, partial-failure compensation, timeout reconciliation, restart-resume, cancellation-failure/manual-intervention |
| 10 | Minimum interface: request CRUD, dashboard, notifications, offer review w/ countdown, booking results, ops view | **Done** - all real; notifications live in a header bell, ops is a Dashboard "Needs attention" section (same data, less clutter when nothing's stuck) |
| 11 | Repeatable scenario runner, 7 scenarios | **Done, 7 of 7** replayable via Simulation (§2) |
| 12 | Automated tests + 100-request load demo | **Done** - 91 tests, load demo re-run fresh (§3) |
| 13 | Live technical review readiness | Covered by this doc set plus the walkthrough in `docs/DEMO_AND_HANDOVER.md` |
| 14 | Six deliverable documents; schema/migrations | **Done** - real Alembic migrations in `backend/alembic/` |
| 15 | Evaluation-weighted priorities honored | Build order matched the weighting (booking > monitoring > tests), not the brief's section order - see Methodology §1 |

## 5. Known gaps, consolidated

- `provisional` component status is schema-forward only, not yet reachable by any real code path.
- Caching/rate-limiting is per-process, not shared - a real limit past one worker process, not yet hit at this scale.
- Free-tier backend sleeps after 15 min idle (disclosed hosting constraint, not a code defect).
- Visual polish deliberately left last (Sec. 10/15's own stated priority).
- One shared package-level hold, not independently-tracked per-component expiries (Sec. 08) - see Methodology §8.
- A full audit (4 passes: live walkthrough, backend read, frontend read, re-verification) found 11
  issues, most notably a cancelled/paused request that could still be booked and a non-deterministic
  Simulation override - all fixed and regression-tested.
