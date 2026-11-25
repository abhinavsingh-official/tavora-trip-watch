# Methodology Report

*Trip Price Watch & Booking - Tavora Product Developer Assignment*
*Candidate: Abhinav Singh · Submission window: 2026-11-18 → 2026-11-25*

Problem breakdown, assumptions, architecture decisions, source selection, package search/ranking,
scheduling, alert policy, holds, failure recovery, and trade-offs - in that order.

---

## 1. Problem breakdown

The system: take a trip request → price it across flights/hotels/cabs on a
schedule → alert the owner on a budget-qualifying, meaningfully-dropped total
→ let them convert an alert into a simulated booking that behaves correctly
under concurrency, time-limited holds, and partial failure. Everything else
in the brief supports that one loop. Grading weights confirm it: booking
correctness/concurrency/recovery (30%) + monitoring/notification correctness
(20%) is half the grade, all on that loop not breaking.

## 2. Assumptions

- **Cabs = pre-booked airport-transfer vehicles**, not app-hailed rideshare -
  rideshare can't be queried for a price by a third party without partner
  access, and the brief's "passenger/luggage capacity" implies a vehicle-class
  decision rideshare doesn't surface.
- **"INR and adults only"** = the product's display/occupancy model, not that
  every upstream source must be INR-native - confirmed against the brief's
  own "no specific provider is prescribed" wording.
- **Demo dates** are 30+ days after the real submission date (2026-11-25) -
  every seeded request is 2026-12-26 or later.
- **7 days + a full-time job ≠ 100%**, and the brief says so. Depth on the
  core loop came before breadth, before scale/polish.

## 3. Architecture decisions

| Decision | Chosen | Rejected because |
|---|---|---|
| Backend | FastAPI | Django+DRF (sync ORM, unneeded batteries); Node (weaker validation); Go/Java (over-engineered for this scale) |
| Database | Postgres | SQLite (no real row-level locking - needed for last-room-contention); MongoDB (weaker multi-doc transactions) |
| Scheduler | In-process APScheduler | Celery+Redis (more infra than 100 requests needs - explicitly not right at 1,000+) |
| Frontend | React + Vite + TS | Next.js (no SSR benefit here); Vue/Svelte (no project-specific upside); plain JS (loses type safety on many state enums) |
| Hosting | Render free tier | No cloud infra, by project constraint; one platform for DB+backend+frontend |

## 4. Source selection

11 research rounds, real registrations and test calls, not just documentation review:

- **Flights - Sabre Dev Studio** (Bargain Finder Max v4): real sandbox, real
  schedule/carrier data; fares are a static test cell (fixed INR/USD rate).
- **Hotels - Hotelbeds Apitude**: real inventory, verified via real hotel
  names; currency EUR, converted to INR at one fixed documented rate.
- **Cabs - simulated**: 6 rounds found no reachable real fare source (Ola/
  CabBazar are B2B-gated). Anchored to real government per-km rate cards and
  the real ₹20-28/km tempo-traveller market.
- **Duffel**: rejected, registration blocked (likely Stripe business-verification gate).
- **RateHawk**: rejected, gated to registered travel companies, no INR pricing.

## 5. Package search and ranking

Cheapest result per component matching the request's own filters - not an
exhaustive market scan (brief: "do not claim market-wide coverage").

- **Flights**: cheapest INR-denominated itinerary from Sabre's response;
  outbound/return are two independent one-way searches.
- **Hotels**: filtered to min star rating, cheapest matching rate; one rate
  line already covers the full requested occupancy (confirmed from the raw response).
- **Cabs**: deterministic by adult count - sedan for ≤3, tempo-traveller for 4+.

Nothing is ever silently zeroed: a failed component is `unavailable`, never
folded into the total as `0`; the package is `complete` only if every part is.

## 6. Monitoring and scheduling

- Manual "check now" and the real 5-min APScheduler cycle call the same
  function (`monitoring.run_check_and_alert`) - one implementation.
- **Rate limits**: Hotelbeds' 8-req/4s burst limit is throttled in code;
  Sabre's 7-day token is cached, not refetched per check.
- **Freshness**: a 4-min TTL cache absorbs repeat checks of the same query
  without changing how often a genuinely new price is fetched - protects
  Hotelbeds' 50-req/day quota (confirmed scarce by exhausting it).
- **At 1,000+ requests**: this architecture needs to change - a single
  in-process scheduler doesn't parallelize blocking HTTP calls, and Hotelbeds'
  quota would need a paid tier or shared caching. Known limitation, not a blind spot.

## 7. Alert policy

Real state machine, tested both automated and live:

- Failed/incomplete check → no alert, no reset.
- First complete package at/under budget → alert once.
- Still under budget → re-alert only on a further 5%+ drop.
- Back over budget → silently resets, so the next crossing alerts again.

## 8. Holds

Reviewing an offer runs a fresh check and freezes that price per component -
flight, hotel, and cab each get their own hold duration (`held_until_flight`
/`_hotel`/`_cab`: 2/3/5 minutes, shortest for the most volatile real-world
quote). Booking is rejected if unreviewed, or if *any* component's hold has
expired, naming which one; the accepted total is derived server-side from the
held observation, never from the client.

## 9. Booking and failure recovery

- **Idempotency**: booking the same notification twice returns the identical
  result - enforced at the app level and by a DB unique constraint (verified
  by booking the same notification three times live).
- **Failure handling**: a forced component failure triggers a real
  compensating cancellation of whatever already succeeded, a `partial`
  status, and an honest `pending` for anything never attempted. The other
  five §09 rows follow the same shape (never lie about what happened, never
  double-do anything) - built once and explained live, not independently
  coded per row, a deliberate depth-over-breadth call.

## 10. Trade-offs and honest limitations

- `PriceObservation.raw_sources` has no pruning/archival policy yet - a real
  retention call needs real scheduler volume to judge against.
- Hotelbeds EUR→INR uses a live daily rate (`app/exchange_rate.py`), with a fixed fallback only if that lookup fails.
- The free-tier scheduler stops ticking while the service sleeps - a hosting limit, not a bug.
- One shared package-level hold, not independently-tracked per-component
  expiries - satisfies the literal requirement since all three are checked
  atomically together.
- Visual polish was left for last, per the brief's own stated priority - the
  one remaining functional gap.

## 11. Build order

Correctness first (the core watch-alert-book loop), then breadth (all three demo users, all seven
§11 scenarios, the 100-request load demo), then a full audit (11 findings, all fixed - including a
cancelled request that could still be booked, and a non-deterministic Simulation override) plus real
Alembic migrations and CI, then UI polish last, per the brief's own stated priority. Real results:
`docs/VERIFICATION_PACKAGE.md`.
