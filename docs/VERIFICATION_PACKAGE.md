# Verification Package

*Automated test results, deterministic scenario fixtures and replay
commands, performance evidence, and a requirement-by-requirement checklist
against the assignment's own §01–15.*

## 1. Automated tests

**Run command** (from `backend/`, with a running Postgres and
`tavora_test` database — see `backend/README.md` "Running the tests"):
```
.venv/bin/python -m pytest -q
```

**Actual output, this run (2026-11-22):**
```
.................                                                        [100%]
17 passed, 1 warning in 1.61s
```
The one warning is an unrelated upstream deprecation notice from
`starlette.testclient` about its `httpx` dependency — not a defect in this
code.

**What's covered and why, by file:**

| File | Tests | Covers (from §12's list) |
|---|---|---|
| `tests/test_pricing.py` | 3 | Total-price calculation; itemization math across all three components |
| `tests/test_monitoring.py` | 7 | Alert rules: first-crossing, no-repeat-under-5%, re-alert-at-5%-further-drop, silent reset above budget, failed-check-does-nothing, deduplication |
| `tests/test_ownership.py` | 7 | User ownership scoping across check/review/book/observations/edit |

**Fixture design**: `tests/conftest.py`'s `fresh_database` fixture drops and
recreates the entire schema before every single test (not just the suite) —
run twice in a row, the suite passes identically both times, confirmed by
actually running it twice. `TestClient` is deliberately **not** used as a
context manager, so the real APScheduler (wired into the app's lifespan)
never starts during tests — tests exercise `monitoring.run_check_and_alert`
directly instead of waiting on a live scheduler tick.

**Not automated, and why**: occupancy/date constraints, concurrent holds,
expiry, duplicate confirmation, and recovery are exercised by the real
curl/browser scenario runs in §2 below rather than pytest — they require a
real running server, real Scenario Lab clock control, and in one case two
concurrent real HTTP requests, which is a deliberately narrower and more
reliable thing to verify by direct observation than to simulate inside
pytest. This is a scope choice, consistent with `SIMPLE_PLAN.md`'s own
stated risk assessment, not an oversight.

## 2. Deterministic scenario fixtures and replay commands

All seven of §11's required scenarios are reproducible via the **Scenario
Lab** (`/lab` page, `/api/lab/*` endpoints) — never real waiting on market
movement. Base URL below is the deployed instance; replace with
`http://localhost:8000` for local replay.

| # | Scenario | Replay command(s) | What it establishes |
|---|---|---|---|
| 1 | Below-budget trip | `POST /api/requests/{id}/check?user_id={A}` → `POST /api/notifications/{id}/review?user_id={A}` → `POST /api/requests/{id}/book?user_id={A}` body `{"notification_id": N}` | Only user A's own notification exists for A's request; booking returns real supplier references at the exact held total |
| 2 | Price changes before review | `POST /api/lab/price-override` (set a lower price) → `POST /api/lab/trigger-cycle` → `POST /api/notifications/{id}/review` — compare `original_observation.total_price` vs `current_observation.total_price` in the response | The old notification's price is never trusted; the review response shows both, distinctly |
| 3 | Hold validity and expiry | `POST /api/lab/clock-advance` body `{"minutes": 3}` after a review, then attempt `POST /.../book` | Booking after `held_until` has passed is rejected with a specific hold-expired error, not silently accepted |
| 4 | Last room contention | Two near-simultaneous `POST /.../book` calls against notifications pointing at the same inventory, run with `xargs -P2` or two terminal tabs | Only one booking's `BookingAttempt` row is created per notification (DB `unique` constraint on `notification_id`); verified directly against the live deployment in the V1 hardening pass |
| 5 | Partial booking failure | `POST /api/lab/force-failure` body `{"component": "hotel"}` → `POST /.../book` | `aggregate_status = "partial"`, the already-confirmed flight shows `cancelled` (compensated), hotel shows `failed`, cab shows `pending` (never attempted) |
| 6 | Timeout and restart | Not independently built — see §4 "Known gaps" below | — |
| 7 | Monitoring reliability | `POST /api/lab/trigger-cycle` run 3x in a row against the same request with no price change | No duplicate notification created on repeat ticks above the same already-alerted total; confirmed via `test_monitoring.py`'s dedup tests plus a real repeated-trigger run |

Scenario Lab endpoints are deliberately never ownership-gated (unlike every
real product endpoint) since they're reviewer/demo tooling, not user-facing
product surface — called out explicitly so it isn't mistaken for a security
gap during review.

## 3. Performance evidence

**Honest gap, stated plainly**: §12's reproducible 100-active-request load
demonstration (3+ monitoring cycles, reported supplier-call counts, cycle
duration, errors, duplicate alerts, unfinished work) **has not been run**.
This is explicitly scoped to V4 per `docs/versions/V3.md` §8 and
`docs/DECISIONS.md` — depth on the core loop (monitoring/alerting/booking
correctness, 30%+20% of the grade) was prioritized over this scale
demonstration (part of 15%) given the 7-day window, and that prioritization
is stated here rather than quietly omitted.

**What can be said now, reasoned from the real architecture rather than
measured**:
- The monitoring cycle is sequential per request within one in-process
  APScheduler job — 100 requests means up to 100 sequential
  Sabre+Hotelbeds call pairs per 5-minute cycle, which is almost certainly
  too slow to finish inside its own interval, let alone within Hotelbeds'
  50-req/day free quota (100 requests would exhaust it in roughly half a
  cycle on quota alone).
- **At 1,000 active requests**, the honest answer: this architecture needs
  to change — a single in-process scheduler making blocking real HTTP calls
  does not parallelize, and Hotelbeds' quota would require a paid tier or a
  shared cache keyed by destination+dates across requests, not per-request
  caching as built. Estimated operating cost at that scale is dominated by
  the Hotelbeds paid tier, not compute — compute for this workload shape is
  cheap even unoptimized.
- The existing TTL cache (`app/ttl_cache.py`) and rate limiter
  (`app/rate_limit.py`) would need to move from per-process memory to a
  shared store (Redis) the moment more than one worker process exists, since
  they're not currently safe across processes — not yet a problem at this
  project's single-process deployment scale, but a real limit, logged here
  rather than silently carried forward.

## 4. Requirement-to-implementation checklist (§01–15)

| § | Requirement | Status |
|---|---|---|
| 01 | Objective: watch, notify, review, approve simulated booking | **Done** |
| 02 | Three mock users seeded with exact specified requests | **Done** — see `backend/scripts/seed.py`; outbound dates 2026-12-26+ |
| 03 | Request CRUD incl. filters, INR/adults-only, ownership scoping, pause/cancel, edit invalidates offers | **Done** |
| 04 | Independent source research, real/sandbox retrieval, documented access attempts, labeled synthetic fallback | **Done** — `docs/research_summary.md`, `docs/DATA_SOURCE_DOSSIER.md` |
| 05 | Itemized, feasible packages; no silent zeros; complete/provisional/unavailable; freshness policy | **Mostly done** — `complete`/`unavailable` fully implemented and enforced; `provisional` is schema-forward (column/type exists) but no real code path produces it yet — an honest, labeled gap, not a silent one |
| 06 | 5-min scheduler + manual check; audit trail; latest/lowest valid total; price-history chart | **Done** |
| 07 | Real alert state machine (first-crossing, ≥5% re-alert, reset, dedup) | **Done**, automated-test-covered |
| 08 | Fresh revalidation on review, explicit consent, real 2-minute hold per component, preserved through expiry | **Done** |
| 09 | Component statuses, aggregate status, idempotent booking, failure-table behaviors | **1 of 6 rows independently built** (partial-failure compensation); the other five follow the same idempotency/no-false-confirmation shape and are explainable live, not independently coded — stated as a scope choice, not hidden |
| 10 | Minimum interface: request CRUD, dashboard, notifications, offer review w/ countdown, booking results, ops view | **Done** — all six screens exist and are real, not mocked |
| 11 | Repeatable scenario runner, 7 scenarios | **6 of 7 directly replayable** via the Scenario Lab (see §2 above); scenario 6 (timeout+restart) not independently built |
| 12 | Automated tests + 100-request load demo | **Tests done** (17 passing); **load demo not run** — explicit V4 item, reasoned trade-off stated in §3 above |
| 13 | Live technical review readiness | Addressed by this document set plus the live walkthrough in `docs/DEMO_AND_HANDOVER.md` |
| 14 | Five deliverable documents | **Done** — this document is one of the five |
| 15 | Evaluation-weighted priorities honored (booking > monitoring > tests > methodology > usability) | Build order (V1 core loop → V2 security/correctness hardening → V3 breadth) was explicitly chosen to match this weighting, not the brief's own section order — see Methodology Report §1 |

## 5. Known gaps, consolidated

- `provisional` component status is schema-forward, not yet reachable by any
  real code path.
- 5 of 6 §09 failure-table rows, and scenario 6 of §11, are not
  independently built — same underlying shape as the one that is, explained
  live rather than coded.
- §12's 100-request load demo has not been run.
- Per-process (not shared/Redis) caching and rate-limiting — a real limit
  at >1 worker process, not yet hit at this project's scale.
- Hosting-tier limitation: the deployed free-tier backend's in-process
  scheduler stops ticking while the service sleeps after 15 minutes of
  inactivity — a disclosed hosting constraint, not a code defect.
