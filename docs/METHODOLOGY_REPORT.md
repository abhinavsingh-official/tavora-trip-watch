# Methodology Report

*Trip Price Watch & Booking — Tavora Product Developer Assignment*
*Candidate: Abhinav Singh · Submission window: 2026-11-18 → 2026-11-25*

This report is a compiled synthesis of `docs/internal/decision-log.md` (the full, dated
decision log kept live throughout the build) and `docs/internal/research-summary.md`
(the full data-source research). Both are included in this repository in
their raw form; this document is the readable narrative version.

---

## 1. Problem breakdown

Stripped to its mechanism, the brief asks for a system that:

1. Takes a structured trip request (origin, destination, dates, occupancy,
   budget, and filters).
2. Periodically prices that request against real inventory across three
   categories — flights, hotels, cab transfers.
3. Alerts the owning user the moment a **complete, valid** package is at or
   under their budget, and again only if the price drops **meaningfully
   further** — not on every check.
4. Lets the user convert an alert into a **simulated** booking that behaves
   like a real one would under concurrency, time-limited holds, and partial
   failure — never silently double-booking, never silently losing track of
   what actually happened.

Everything else in the 15-section brief is detail in service of making that
one mechanism trustworthy, not a separate thing to build. The grading weights
confirm this reading directly: 30% booking correctness/concurrency/recovery
+ 20% monitoring/notification correctness is more than half the grade,
concentrated on that one loop not breaking.

## 2. Assumptions

- **"Cabs" means pre-booked outstation/airport-transfer vehicles** (a
  Kiwitaxi/Savaari-shaped fixed quote), not app-hailed rideshare (Uber/Ola/
  Rapido) — those platforms cannot be queried for a price by a third party
  without being a registered partner, and the brief's own wording ("cab
  passenger/luggage capacity") implies a vehicle-class decision that
  app-hailed rideshare doesn't surface pre-trip. Full reasoning and
  competitor research in `research_summary.md` §6.4.
- **"Use INR and adults only"** means the product's displayed currency and
  occupancy model, not that every upstream source must natively be
  INR-denominated or India-based — confirmed against the brief's own §04
  wording ("no specific provider... is prescribed") before assuming
  otherwise.
- **Submission demo dates** must be at least 30 days after the *actual*
  submission date (2026-11-25), not the receipt date — outbound dates in
  every seeded request are 2026-12-26 or later, safely past that boundary.
- **A 7-day window with a full-time job cannot complete this assignment to
  100%**, and the brief says so explicitly. Priority was given to depth on
  the core loop (V1-V2) before breadth (V3) and scale/polish (V4), per the
  grading weights, not the document's own section order.

## 3. Options considered — architecture

Full reasoning, including a plain-language and technical definition for
each, is in `DECISIONS.md`'s "Architecture" entry. Summary:

| Decision | Chosen | Rejected, and why |
|---|---|---|
| Backend | FastAPI | Django+DRF (sync-by-default ORM fights an I/O-bound workload; unneeded batteries); Node.js (weaker validation than Pydantic, less candidate depth for the live review); Go/Java (over-engineered for the tested scale, "complexity doesn't earn credit by itself" per §15) |
| Database | Postgres | SQLite (file-level locking, not real row-level concurrency control — directly needed for §11's last-room-contention scenario); MongoDB (weaker multi-document transaction guarantees for this relationally-shaped problem) |
| Scheduler | In-process APScheduler | Celery+Redis (more infrastructure than this scale — 100 requests, §12 — actually needs; explicitly logged as *not* the right pick at 1,000+ requests, an honest limit, not an oversight) |
| Frontend | React + Vite + TypeScript | Next.js (no SSR/SEO benefit for an authenticated dashboard app); Vue/Svelte (real context-switch cost for no project-specific benefit); plain JS (loses compile-time safety on this system's many state enums — `complete`/`provisional`/`unavailable`, hold `valid`/`expired`, booking `confirmed`/`partial`/`failed`/`cancelled`/`pending`) |
| Hosting | Render (free tier) | No AWS/cloud-provider infra, per the project's own standing constraint; one platform for Postgres + backend + frontend, simplest to manage solo |

## 4. Source selection

Full research (11 rounds, cited sources, verified-vs-assumed discipline) is
in `docs/internal/research-summary.md` and `docs/internal/research-notes-raw.md`. Final state, confirmed by
**real registration and real test calls**, not just documentation review:

- **Flights — Sabre Dev Studio** (Bargain Finder Max v4). Real company, real
  sandbox, schedule/carrier data confirmed real; fares confirmed from a
  static test cell (same INR/USD exchange rate repeats across every result).
- **Hotels — Hotelbeds Apitude** (geolocation-based availability search).
  Real company, real inventory — confirmed via real, independently-checkable
  hotel names (e.g. Kenilworth Beach Resort, The Zuri White Sands Goa); fare
  currency confirmed EUR via a real `CheckRates` call, converted to INR at a
  documented fixed rate (not a live FX feed).
- **Cabs — simulated**, after six research rounds found no reachable real
  fare source for this category (every real candidate — Ola's own Outstation
  API, CabBazar's documented API — is B2B-gated with no guaranteed access
  window). Anchored to real reference data: official government per-km RTO
  rate cards and the real ₹20–28/km tempo-traveller market range, not an
  arbitrary number.
- **Duffel was evaluated and rejected** after a real registration attempt
  was blocked (most likely a Stripe-based business-verification step) —
  logged as the working explanation, not an assumed certainty.
- **RateHawk was evaluated and rejected** after a real registration attempt
  confirmed it's gated to registered travel companies and has no INR
  pricing regardless.

## 5. Package-search and ranking method

For each component, the cheapest result matching the request's own filters
is selected — not an exhaustive market scan (the brief explicitly says "do
not claim market-wide coverage," §05):

- **Flights**: Sabre's Bargain Finder Max v4 response is scanned for the
  cheapest itinerary whose fare is already INR-denominated (Sabre's own
  field, no conversion needed); outbound and return legs are two independent
  one-way searches.
- **Hotels**: Hotelbeds' geolocation search response is filtered to rooms
  meeting the requested minimum star rating, then the cheapest matching rate
  is selected. A single rate line item already represents the full
  requested occupancy (e.g. `"rooms": 2, "adults": 4"` for a 2-room, 4-adult
  request) — confirmed by inspecting the raw response directly, not assumed.
- **Cabs**: deterministic by adult count — a sedan-class flat quote for ≤3
  adults, a tempo-traveller-class quote for 4+ adults, each leg priced
  independently.

Nothing is ever silently zeroed — a missing/failed component status is
reported as `unavailable`, never a `0` folded into the total (§05's explicit
rule), and the whole package is `complete` only if every component is.

## 6. Monitoring and scheduling strategy

- A manual "check price now" button and a real, automatic 5-minute
  APScheduler cycle both call the exact same function
  (`app/monitoring.run_check_and_alert`) — one implementation, not two that
  can drift.
- **Rate-limit respect**: Hotelbeds' documented 8-requests-per-4-seconds
  burst limit is enforced with a thread-safe throttle; Sabre's 7-day auth
  token is cached in memory, not re-fetched per check.
- **Freshness policy**: a short (4-minute) TTL cache absorbs rapid repeat
  checks for the *same* query without changing how often a genuinely new
  real price is fetched — protects Hotelbeds' scarce 50-requests/day free
  quota, confirmed scarce by exhausting it during research.
- **At scale (1,000+ active requests)**: the honest answer is this
  architecture would need to change — a single in-process scheduler making
  blocking real HTTP calls sequentially does not parallelize, and Hotelbeds'
  real quota would need a paid tier or a shared caching layer across
  requests targeting the same destination/dates. Logged as a known
  limitation, not a blind spot (Sec. 12 explicitly asks for this answer).

## 7. Alert policy

The real state machine (not a placeholder), verified with both automated
tests and real live-server runs:

- A **failed or incomplete** check does nothing either way — no alert, no
  reset, and the alert memory is untouched.
- The **first** time a complete package is at or under budget, alert once.
- While it stays under budget, alert again only if the price has dropped
  **at least 5% further** below the total last alerted at.
- A complete package **back over budget** silently clears that memory, so
  the next crossing is treated as a first crossing again.

## 8. Holds

Reviewing an offer runs a real, fresh check (not a cached read) and freezes
that specific observation's price for **2 minutes**
(`notifications.held_until`). Booking is rejected — with a specific,
distinguishable error — if no review has happened yet, or if the hold has
expired; the accepted total is derived from the held observation
**server-side**, never trusted from whatever the client sends.

## 9. Booking and failure recovery

- **Idempotency**: booking the same notification twice returns the
  identical result, enforced both at the application level and with a
  database-level unique constraint (the only thing actually atomic under two
  near-simultaneous requests) — verified by booking the same notification
  three times through the real running app.
- **One failure scenario, built completely**: a Scenario-Lab-forced
  component failure during booking triggers a real compensating
  cancellation of whatever already succeeded, a `partial` aggregate status,
  and an honest `pending` (not `confirmed`/`failed`) status for anything
  never attempted. The other five rows of §09's failure table follow the
  identical shape (don't lie about what happened, don't do the same thing
  twice) and are explainable in the live review, not independently coded —
  a deliberate depth-over-breadth choice given the time budget.

## 10. Trade-offs and honest limitations

*(Updated after V7 — see `docs/versions/V7.md` for what changed, and
`docs/internal/audit-log-2026-11-23.md` for the full audit that drove most of it.)*

- `PriceObservation.raw_sources` (the full raw API response per check) has
  no pruning/archival policy — deliberately not fixed reflexively; a real
  retention decision deserves its own consideration once real scheduler
  volume exists to judge it against.
- Hotelbeds' EUR→INR conversion uses one documented fixed rate, not a live
  FX feed — labeled as approximate everywhere it's shown.
- The deployed free hosting tier's in-process scheduler stops ticking while
  the service is asleep (15 min idle) — a real, disclosed hosting-tier
  limitation, not a code bug.
- One shared package-level hold rather than independently-tracked
  per-component hold expiries (Sec. 08) — satisfies the literal requirement
  since all three components are checked atomically together, but was only
  explicitly written down as its own decision during V7's requirements
  re-read, not from the start.
- Visual polish was deliberately left for last, per the brief's own stated
  priority (§10/§15) — the one remaining functional gap, now that V7's audit
  and requirements re-read have closed everything else found.

## 11. What actually got built, version by version

See `docs/versions/V1.md` through `V7.md` for the full per-version record
(what's new, architecture active, data sources, simulation controls, stress
tests run and their results, decisions made, honest gaps) — each version
independently demoable, each one adding correctness (V1→V2), breadth (V3),
closing remaining gaps (V4), UI polish (V5-V6), or fixing a full audit's
findings plus real schema migrations and CI (V7) to the one before it, not
unrelated new scope. As of V4, all six Sec. 09 failure-table rows, all
seven Sec. 11 scenarios, and the Sec. 12 100-request load demonstration are
done; as of V7, all 11 audit findings and one further requirements gap
(Sec. 06's lowest-total/price-history chart) are fixed too - see
`docs/VERIFICATION_PACKAGE.md` for the real captured results.
