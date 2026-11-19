# Tavora Trip Price Watch & Booking — Research Summary

*Decision log and domain/competitor/data research, phase 1 (pre-architecture).
Compiled 2026-11-19 from `docs/NOTES.md` and `docs/DECISIONS.md`.*

---

## 1. Timeline & constraints

- **Received:** Wednesday night, 2026-11-18.
- **Demo:** following Wednesday night, 2026-11-25 (7-calendar-day window).
- **Demo travel dates** shown in the product must be on/after **2026-12-25**, to stay
  clear of the assignment's "30+ days after submission" rule.
- **No AWS/cloud-provider infrastructure** for this project — confirmed explicitly
  with the candidate. Hosting, when it's decided, follows a lightweight PaaS pattern
  (Vercel/Render-style), not AWS/GCP/Azure.

## 2. Stack — what's settled, what's deliberately still open

| Layer | Status | Note |
|---|---|---|
| Backend | **Settled: Python + FastAPI** | Explicit preference; consistent with rest of portfolio |
| Frontend | Open | Not discussed yet — deliberately deferred |
| Database | Open | Leaning Postgres (concurrency/locking needs), not yet decided |
| Scheduler/queue | Open | Leaning APScheduler for v1, not yet decided |
| Data sources per category | Open | Needs its own research — see §5 |

**Why architecture is being deferred on purpose:** the brief rewards understanding the
problem (source research 20%, monitoring/notification correctness 20%, booking
correctness/concurrency/recovery 30%) far more than framework choice. The explicit
plan is: understand the domain, the real data landscape, and real competitor products
*first*, and only then settle stack questions — not the reverse.

## 3. What the assignment actually asks for, stripped to the mechanism

A system that:

1. Takes a structured **trip request** (origin, destination, dates, budget, filters).
2. Periodically **prices it** against real (or honestly-labeled simulated) inventory.
3. **Alerts** the owning user the moment a complete, valid package crosses their
   budget — or drops meaningfully further.
4. Lets them convert that alert into a **simulated booking** that behaves correctly
   under concurrency, expiry, and partial failure.

### Reconciling a friend's pointers against the actual brief

| Friend's pointer | Maps to | Note |
|---|---|---|
| Competitor research / which APIs | §04 (data sourcing) | Not optional — 20% of the grade |
| "Logical watcher" | §06 monitoring scheduler | 5-min cycle + manual trigger + audit trail — the system's heartbeat |
| Browse → leave → price drops → notify | Related, but **not** the brief's actual mechanism | §07's real state machine is stricter: first budget-crossing alert, then only re-alert on ≥5% further improvement, reset only by a valid above-budget observation |
| Load balancer / domain / hosting | §14 "runnable product" | Real, but low weight; explicitly not AWS here |
| loguru / log schema | Supports §06 audit trail, §10 ops view | Good practice, in service of monitoring correctness, not a separate grading line |
| CI/CD, configmap/secret split | Supports §14 "code repository" deliverable | Worth real CI; lighter on secrets ceremony for a solo prototype |
| SDLC starting from data | Matches the brief's own ordering | data → packages → monitor → notify → booking — the actual order being followed |

### What "absolute base" (MVP) has to mean

Given the grading weights, the base slice is **not** a working UI. It's:

- One request,
- one real (or honestly-labeled simulated) pricing source per category,
- a correct monitor → alert cycle,
- a booking flow that survives the full failure-mode table (§09).

UI polish and source breadth are additions once that core loop is provably correct.

## 4. Tavora's real site — context only, not a clone

Looked at two live pages for UX/domain context. Explicit instruction followed: this
build must **not** be a clone — only a small demo inspired by real patterns.

**`/plan` (browse/discovery page):**
- A trip-discovery listing — "Where / When / Who" filters, 52 results grouped by
  state, plus combo "pair" cards.
- Price framing: *"Every price is per person, all in... the overnight bus or train,
  the stay and the rides there"* — Tavora already thinks in the same three components
  (transport / stay / local transfer) this assignment cares about, just bundled into
  one "from" price on the listing page.
- **No price-watch, alert, or notify-me feature anywhere.**

**`/trip/{slug}` (e.g. Manali) — a 6-step wizard:** Travel → Ride → Stay → Extras →
Return → Review.
- Each step's footer repeats: **"we confirm the live price before you pay."** This is
  Tavora's own version of the assignment's §08 requirement (revalidate + fresh consent
  before booking) — real-world precedent that this is the correct instinct, not an
  invented requirement.
- Pricing accumulates step by step; there's no upfront itemized total — notably, the
  assignment is **stricter** than Tavora's own live UI here, since it explicitly
  requires an upfront itemized breakdown.
- No price-watch feature on this page either. This strongly suggests the capability
  being built doesn't exist on Tavora's real product today — the assignment is testing
  whether something genuinely new can be designed, not a re-implementation of
  something they already ship.

**Takeaway:** the offer-review screen (§08/§10) should echo Tavora's own "confirm live
price before you pay" language, and the three price components line up with how
Tavora itself frames pricing — a good sign the assignment's model matches how the
company actually thinks about trips.

## 5. Competitor landscape — how real price-watch tools work

Distinguishing **verified** (stated directly by the company) from **unverified**
(marketing claim, no independent audit) throughout.

**ixigo (closest real-world analog):**
- "Fare Intelligence" = Fare Prediction (domestic flights, ≤30 days out, historical
  trend-based) + Fare Alerts (price-drop notifications on tracked routes).
- **"Smart Lock"** — the single most relevant precedent: continuously monitors fares
  against a target budget, locks the fare once found within budget, and covers the
  difference (up to ₹4,000 domestic / ₹8,000 international) if the price rises after
  locking. Caveat (verified): the lock fee is non-refundable, and the guarantee covers
  fare only, not seat availability.
- This maps almost exactly onto the assignment's §06–§08 (monitor → budget-crossing
  alert → hold) as a shipped product.

**Google Flights / Hopper (international reference):**
- Both trend/history-based, not real-time guarantees. Hopper's "Price Freeze" locks a
  fare for up to 20 days for a $10–20 deposit — another real precedent for the
  hold/lock mechanic, though paid and much longer than this project's 2-minute hold.
- All vendor accuracy claims (Hopper's "95% accuracy," ixigo's "up to 40% savings")
  are unverified marketing numbers — treated as such throughout, and used as a
  methodology point: don't anchor this system's own confidence language on
  unverifiable vendor claims.

**Takeaway:** the "lock a price for a short window, cover/honor it if things move" vs.
"re-quote and get fresh consent after expiry" split (§08) is exactly how the two best
real products in this space already work. This isn't an invented mechanic — it's a
more rigorous, engineering-correct version of a pattern that already exists
commercially.

## 6. Real data-source landscape (flights / hotels / cabs, India)

Checked whether genuinely free/sandbox access exists per category, since §04 requires
real-or-sandbox retrieval *where accessible*, and an honestly-labeled simulated
source *where it is not*.

**Flights:**
- **Amadeus Self-Service** — conflicting reports: a documented free Test tier exists,
  but a 2026 third-party guide claims the free portal was decommissioned mid-2026.
  Unresolved without directly registering.
- **Duffel** — strongest confirmed free sandbox: unlimited test balance, a dedicated
  test airline ("Duffel Airways"), deterministic test routes. **Limitation (verified
  directly from Duffel):** test-mode prices are explicitly not real/live, even in test
  mode.
- **Kiwi.com Tequila** — reportedly closed to public self-serve since May 2024,
  conflicting reports on a limited free tier remaining.
- **SerpApi** — scrapes Google Flights/Hotels results; free tier size disputed
  (100–250/month); real prices, but search-engine-mediated, not a direct supplier API.

**Hotels:**
- **Booking.com Demand API** — has a real sandbox, but requires first becoming an
  approved Managed Affiliate Partner — not self-serve within a 7-day window.
- No confirmed free, India-specific hotel pricing API found. Scraper-based
  alternatives exist but are ruled out — the assignment explicitly forbids bypassing
  access controls.

**Cabs / airport transfers:**
- **Ola** — documented Ride Estimate API, but access is case-by-case, invite-only via
  email to their affiliates team.
- **Uber** — no evidence found of current public India developer access.
- Scraped fare figures (e.g. ₹150–218 airport pickup range) are directionally useful
  for building a realistic synthetic fare model, but not citable as live prices.

**Bottom line (an evidenced finding, not an assumption):** free, real-time access
across all three categories, for India routes, within a 7-day window, is not
realistically available. Duffel's test mode is the strongest candidate for a
genuinely real (if non-live-priced) flight integration; hotels and cabs most likely
need clearly-labeled synthetic sources with realistic, cited contracts grounded in
this research — exactly what §04 asks for when a category is inaccessible.

## 7. Open gaps

- **Not yet researched:** hotel-specific and cab-specific competitor products
  (parallel depth to the flight-price-watching research done on ixigo/Google/Hopper).
- **Not yet decided (intentionally):** frontend framework, database, scheduler,
  final per-category data-source selection. These wait until the domain research
  above is considered complete.

---

*Full raw research (uncondensed, with every source link) lives in `docs/NOTES.md`.
The formal options-considered log for the Methodology Report lives in
`docs/DECISIONS.md`.*
