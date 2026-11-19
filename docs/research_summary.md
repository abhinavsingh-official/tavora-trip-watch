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
| Data sources per category | Open | Needs its own research — see §6 |

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

| Page | What it is | Price-watch feature? | What we take from it |
|---|---|---|---|
| `/plan` | Browse/discovery listing — "Where/When/Who" filters, 52 results grouped by state, plus combo "pair" cards | **None** | They already decompose price into transport + stay + local rides, just bundled into one "from ₹X" listing figure — same three components this assignment cares about |
| `/trip/{slug}` (e.g. Manali) | A 6-step wizard: Travel → Ride → Stay → Extras → Return → Review | **None** | Every step footer repeats *"we confirm the live price before you pay"* — their own version of §08 (revalidate + fresh consent before booking). Pricing accumulates step-by-step with no upfront itemized total — our assignment is **stricter** here, since it explicitly requires one |

**Takeaway:** the offer-review screen (§08/§10) should echo Tavora's own "confirm live
price before you pay" language. Neither page has anything resembling a price-watch,
alert, or lock feature — this strongly suggests the capability being built here
doesn't exist on Tavora's real product today, i.e. the assignment is testing whether
something genuinely new can be designed, not a re-implementation of something they
already ship.

## 5. How we're judging competitors and data sources

Two different things are being evaluated below, each against its own fixed set of
criteria, applied consistently so the comparison is defensible rather than a vibe:

**Competitor products** (§6) — existing shipped tools that do something like what this
assignment asks for. Judged on:

| Criterion | What it means |
|---|---|
| **Mechanism** | Is the core logic a *trend/history-based prediction*, an *observed-price tracker* (poll & compare, our own pattern), or a *real-time multiplier* applied at request time? |
| **Core feature** | The specific capability relevant to us — price alert, price lock/hold, or a paid freeze/deposit |
| **Guarantee terms** | Exact numbers the company states (coverage caps, window length, fees) — "none" if there's no guarantee at all |
| **Claim verification** | **Verified** (stated directly in official docs/company press) vs. **Unverified** (marketing copy, third-party claim, no independent audit) |
| **Relevance to our §06–08 design** | High / Medium / Low / None — how closely the mechanism maps onto this project's monitor → alert → hold loop |

**Data sources** (§7) — real or sandbox APIs we could actually integrate against per
category, since §04 requires real-or-sandbox retrieval *where accessible* and an
honestly-labeled simulated source *where it is not*. Judged on:

| Criterion | What it means |
|---|---|
| **Access model** | Free self-serve / free sandbox / invite-only / requires partnership / paid / scrape-only |
| **Price realism** | Live real market price / real historical data / synthetic test data (realistic contract, fake numbers) / scraped real price |
| **India coverage** | Confirmed directly / vendor-claimed but unverified / not found |
| **Reachable in a 7-day window** | Yes / No / Uncertain — can this actually be set up and called before the demo |
| **Verification status** | Verified (official docs) / Conflicting (sources disagree) / Unverified claim |
| **Access-control risk** | None / Some (ToS grey area) / Ruled out (assignment explicitly forbids bypassing access controls) |
| **Verdict for this project** | Use / Reject / Fallback — anchor for a synthetic model |

## 6. Competitor landscape

### 6.1 Flights

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance to our design |
|---|---|---|---|---|---|
| **ixigo — Fare Intelligence** | Trend/history-based prediction (≤30 days out, domestic only) | Fare Prediction + Fare Alerts (drop notifications on tracked routes) | None (prediction/alert only) | Verified (ixigo's own docs: domestic-only, 30-day window) | Medium — alerting mechanism parallels §07 |
| **ixigo — Smart Lock** | Continuous fare monitoring against a target budget | Locks fare once found within budget | Covers fare rise after lock, up to ₹4,000 domestic / ₹8,000 international; lock fee non-refundable; covers fare only, not seat availability | Verified (company press/docs) for the mechanism and caps; **unverified** for internal implementation | **High** — almost exactly our §06–08 (monitor → budget-crossing alert → hold) as a shipped product |
| **Google Flights — Price Forecast/Alerts** | Trend/history-based prediction | 7-day direction estimate with stated confidence; drop alerts | None | Verified (Google's own description, via secondary source) for the mechanism; accuracy figures unverified | Low — prediction only, no hold/lock |
| **Hopper — Price Freeze (flights)** | N/A (deposit product, not a prediction mechanism per se) | Lock a fare for up to 20 days for a $10–20 deposit | Deposit counts toward fare if booked in-window; otherwise becomes a travel credit or is lost | Verified (Hopper's own terms) for mechanics; **unverified** accuracy claims ("95% accuracy," marketing) | Medium — real hold/lock precedent, but paid and much longer-duration than our 2-minute hold |

**Takeaway:** the "lock a price for a short window, cover/honor it if things move" vs.
"re-quote and get fresh consent after expiry" split (§08) is exactly how the two
highest-relevance real products (ixigo Smart Lock, Hopper Price Freeze) already work.
This isn't an invented mechanic — it's a more rigorous, engineering-correct version of
a pattern that already exists commercially, built at prototype scale (2-minute hold
vs. their paid, multi-day holds).

### 6.2 Hotels

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance to our design |
|---|---|---|---|---|---|
| **Hopper — hotel price prediction** | Trend/history-based prediction (historical price + review signals) | Rise/fall forecast for a specific hotel | None | Verified mechanism description; **unverified** accuracy ("95% accuracy" — third-party claim) | Low — prediction only |
| **Hopper — Price Freeze (hotels)** | N/A (deposit product) | Lock a specific hotel's rate for up to 60 days (14/21-day variants reported by other sources/partners) | Covers price rise during freeze window up to ~$100 cap, with a max-difference threshold; not a reservation with the hotel — framed as price insurance | Verified (company press) for mechanics; terms reported inconsistently across sources (likely changed over time / partner-specific, e.g. Capital One's Hopper-powered portal) | Medium — real hold/lock precedent, paid, much longer window than ours |
| **Kayak — hotel price forecast** | Trend/history-based prediction | 7-day rise/fall direction from historical + real-time data | None | Verified mechanism (Kayak's own description); no independent accuracy audit found | Low — prediction only |
| **Scraping-based trackers (e.g. PageCrawl)** | **Observed-price tracking** — polls a specific booking-page URL at intervals, alerts on an actual observed rate change | Price-drop alert on a tracked page | None | Verified (how the tool works is documented by the vendor itself; not an accuracy claim, just a mechanism) | **High** — structurally the closest real analog to our own §06 poll → compare → alert cycle |
| Booking.com / Trivago internal mechanism | Unknown | — | — | **Not found** — no public documentation of their own price-alert internals surfaced by this research | N/A |

**Takeaway:** hotels split into the same two mechanisms seen on flights — trend
prediction (Hopper, Kayak) vs. observed-price tracking (scraping trackers). **Our own
design sits in the tracking camp, not the prediction camp** — worth stating explicitly
in the Methodology Report: this is a price *watcher*, not a price *predictor*, a real
and named category of existing tool, just not the most heavily marketed one.

### 6.3 Cabs

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance to our design |
|---|---|---|---|---|---|
| **Uber — surge pricing** | **Real-time multiplier** — automatic, driven by hyperlocal rider demand vs. driver availability at request time; company states it also factors in market-condition forecasts | None (not trackable/alertable — it's a live price, not a quote) | Emergency surge caps applied by Uber's own teams in major events | Verified (Uber's own pages) for the core mechanism; third-party claims of explicit weather/event/traffic inputs **unverified** | **None** — not a trackable quote at all, structurally incompatible with a price-watch pattern |
| **Ola — surge pricing** | Reportedly the same general supply/demand multiplier concept | None | Unknown | **No published detail found** — least documented of anything researched | None |
| India regulatory surge cap (2020 → 2025 Motor Vehicle Aggregator Guidelines) | N/A (regulation, not a product) | Caps surge at 1.5x base fare (2020) → 2x base fare at peak (2025 revision); floor of 50% of base off-peak | Legally mandated ceiling/floor | Verified (government guideline coverage) | **High relevance as a data anchor** — gives a real, citable multiplier range (0.5x–2x) for a synthetic cab-fare model, not a competitor feature |

**Takeaway:** **no real-world "cab fare watcher" product exists anywhere** —
consistent with Tavora's own site having no price-watch feature either. A cab fare
isn't a trackable quote the way a flight or hotel price is; it's a live multiplier.
This means the cab leg of this system needs its own justification in the Methodology
Report, distinct from flights/hotels — modeling a real-time surge multiplier against a
base fare, not tracking a quoted price over time. The regulatory cap (0.5x–2x) is the
most useful finding here: a real anchor for an honest synthetic model, not a feature
to imitate.

## 7. Data-source landscape (India)

### 7.1 Flights

| Source | Access model | Price realism | India coverage | Reachable in 7 days | Verification status | Access-control risk | Verdict |
|---|---|---|---|---|---|---|---|
| **Amadeus Self-Service** | Conflicting — docs describe a free Test tier; a 2026 third-party guide claims the free portal was decommissioned mid-2026 | Real historical/cached test data (if the tier still exists) | Vendor-claimed, unverified | **Uncertain** — would need to actually attempt registration to resolve | Conflicting | None | **Reject for now** — unresolved access, no time to gamble on it |
| **Duffel** | Free self-serve sandbox ("test mode") | **Synthetic test data** — explicitly confirmed non-real/non-live prices, even in test mode, via a dedicated test airline | N/A (test airline, not real carriers) | **Yes** — confirmed free, immediate, unlimited test balance | Verified (Duffel's own help center) | None | **Use** — strongest confirmed free sandbox; the realistic API contract is the value, not real prices |
| **Kiwi.com Tequila** | Reportedly closed to public self-serve since May 2024; invitation/partnership-only per most sources | Real (when accessible) | N/A | **No/Uncertain** | Conflicting | None | **Reject** — inconsistent reports, can't rely on it |
| **SerpApi (Google Flights scrape)** | Free tier (disputed size: 100–250/month) | **Real, scraped** — mirrors actual Google Flights search results | Yes (any Google-indexed route) | Yes, within free-tier limits | Conflicting on exact quota | None (scrapes a public search results page, not an airline's protected system) | **Possible supplement** — real prices, but search-engine-mediated rather than a direct supplier API; free-tier quota too uncertain to be a primary source |
| **Travelpayouts — Aviasales Data API** (round 2) | Free, self-serve — sign up + connect to the Aviasales program, no extra approval | **Real, but historical/trend** — price-calendar and popular-route data via GraphQL, not a live point-in-time quote | Yes (any Aviasales-covered route, incl. India) | Yes | Verified (Travelpayouts' own support docs) | None | **Use as a supplementary signal** — a real baseline/trend range to calibrate against, not a live-quote replacement |
| **Travelpayouts — Aviasales real-time Flight Search API** (round 2) | Gated — "access provided only to projects with MAU starting from 50,000" | Real, live | Yes | **No** — MAU requirement makes this unreachable for a new solo prototype | Verified (Travelpayouts' own docs) | None | **Reject** — real but structurally inaccessible for this project's scale |
| **Skyscanner — official partner API** (round 2) | No public free tier at all; commercial partnership only (commonly ~100K MAU) | Real (if access were granted) | Yes | No | Verified (no free path exists) | None | **Reject** — no legitimate self-serve path exists |
| **Skyscanner — unofficial RapidAPI/Apify scraper wrappers** (round 2) | "Free tier" advertised (e.g. 100 calls/month), but these are third-party scrapers, not Skyscanner's own API | Real (scraped), but unofficial | Yes | Yes (if used) | Unverified/unstable — one Stack Overflow report notes an endpoint already pulled from RapidAPI | **Ruled out** — scraping a protected search product is exactly what §04's "do not bypass access controls" forbids | **Reject outright** — not just deprioritized, explicitly disallowed by the brief regardless of convenience |
| **Sabre Dev Studio** (round 3) | **Free self-serve test key** — Sabre's own site: immediate signup, no accreditation for the test key itself; browser-based "Try It Out" per endpoint | Same shape as Duffel — third-party guides describe test-key data as "limited or simulated," not live | Unconfirmed for India specifically | **Yes** — per Sabre's own docs | **Conflicting** — a third-party comparison (Geekflare) claims no self-serve path exists at all, directly contradicting Sabre's own site; treating Sabre's own docs as authoritative per our verification standard | None | **Credible second sandbox alongside Duffel** — doesn't change the "no live flight prices" conclusion, but a real second GDS contract to reference/cross-check |
| **Direct Indian carrier APIs** (IndiGo/Air India/SpiceJet/Akasa — round 3) | **None found** — no public fare API from any of the four; the only developer-facing mention is IndiGo's fares distributed *through* Travelport (a GDS partner), not a direct carrier API | — | N/A | No | Verified (checked directly, nothing found) | None | **Reject — confirmed not to exist**, not merely unsearched |
| **AviationStack / FlightLabs** (round 3) | Free tier exists (~100 req/month, AviationStack) | AviationStack is schedule/status-focused, pricing data vendor-claimed and unverified; FlightLabs' "Flight Prices" endpoint is documented as returning "scraped flight options," not a licensed feed | Unconfirmed | Uncertain | Unverified | Possible (if FlightLabs is in fact a scraper) | **Reject** — not a credible licensed fare source either way |

### 7.2 Hotels

| Source | Access model | Price realism | India coverage | Reachable in 7 days | Verification status | Access-control risk | Verdict |
|---|---|---|---|---|---|---|---|
| **Booking.com Demand API** | Requires becoming an approved Managed Affiliate Partner first; sandbox only unlocks after that | Real (sandbox mirrors live inventory once access is granted) | Yes, if access is granted | **No** — partnership approval won't complete in a 7-day window | Verified (Booking.com's own docs — the gate itself, not a rumor) | None | **Reject for this timeline** — real documented sandbox, just not reachable in time |
| **Hotelbeds (HBX Group) Apitude API** (round 2) | **Free self-serve** — "Get your free API key," immediate, no partnership approval needed | **Unresolved** — official docs don't state whether evaluation-environment content/prices are real or a separate synthetic test dataset; sources conflict (one partner guide implies real content, one unofficial analysis suggests anomalous/non-live test prices) | Unconfirmed for India specifically, needs direct check | **Yes** — registration and first calls are immediate | Conflicting on realism, but the access model itself is verified from the official developer portal | None | **Strongest hotel candidate found — register and test directly** rather than defaulting straight to synthetic; capped at 50 requests/day on the free evaluation key |
| **TBO Holidays** (round 2, re-checked) | B2B only — requires becoming a vetted, registered travel agency (security deposit or credit line) | Real (if access were granted) | Yes | **No** — vetting process won't complete in a 7-day window | Verified (no self-serve developer path exists) | None | **Reject for this timeline** — same shape of gate as Booking.com |
| **MakCorps / Apify-style scrapers** | Paid per-call, or ToS-risky scraping | Real (scraped) | Yes | Yes (paid) | Unverified pricing/coverage claims | **Some/Ruled out** — the assignment explicitly forbids bypassing access controls | **Reject** — explicitly disallowed by the brief, regardless of cost |
| **RateHawk (Emerging Travel Group) ETG API v3** (round 3) | **Conflicting** — RateHawk's own marketing page implies self-serve ("register → get your free API key → certify"); a third-party integrator describes a gated process instead (contact as a registered travel company, sign an API agreement, then receive a sandbox key) | Real (if access is genuinely self-serve) | Unconfirmed | **Unclear** — depends on which access description is accurate | **Conflicting**, same shape of uncertainty as Amadeus in round 1 | None | **Unresolved — would need direct registration to settle**, not assumed either way |
| **Agoda** (round 3) | Partnership-gated ("Online Affiliates/MSE" model); API access handled case-by-case, not self-serve | Real (if access were granted) | Yes | No | Verified (no free self-serve path found) | Unofficial scraper alternatives exist (Apify, Parse.bot) but are ToS-risky | **Reject** — official path is gated, scraper alternatives ruled out on the same grounds as other scrapers |

### 7.3 Cabs / airport transfers

| Source | Access model | Price realism | India coverage | Reachable in 7 days | Verification status | Access-control risk | Verdict |
|---|---|---|---|---|---|---|---|
| **Ola Ride Estimate API** | Invite-only, case-by-case via email to affiliates team | Real (if granted access) | Yes | **Uncertain/unlikely** — no guaranteed turnaround | Verified (Ola's own docs describe the gate) | None | **Reject for this timeline** — real but not reliably reachable in time |
| **Uber (India developer access)** | Sandbox itself is usable without privileged scopes, but the price-estimates endpoint is gated behind Uber's approval | Real (if granted access) | Unconfirmed | No | Verified (Uber's own docs) | **Confirmed ToS conflict (round 3)** — Uber's API Terms of Use explicitly prohibit using the API to offer price comparisons with competitive third-party services, directly relevant to a trip price-watch tool | **Reject — not just inaccessible, contractually in conflict with this project's purpose** |
| **Rome2Rio** (round 2, checked and ruled out) | Was free/self-serve historically for routing | **Not a fare source at all** — Rome2Rio's own documentation states the API does not provide live transit prices or airfares, and recommends pairing it with a separate airfare provider | N/A | N/A | Verified (Rome2Rio's own documentation) | None | **Reject — out of scope**, not a pricing API regardless of access terms |
| **Google Distance Matrix (legacy) / Routes API "Compute Route Matrix"** (round 2) | **Free, self-serve** — standard Google Cloud API key, no partnership gate | **Not a fare source** — returns real driving distance/duration, not a price | Yes — confirmed real India-specific free quota | Yes — immediate | Verified (Google's own pricing pages); **70,000 free events/month specifically for India**, vs. 10,000 globally | None | **Use as a supporting input** — real geographic distance to ground a synthetic cab-fare formula, not a price source itself |
| Scraped fare figures (e.g. ₹150–218 airport pickup range across operators) | Scrape/aggregator pages | Real figures, but a point-in-time sample, not a live feed | Yes | Yes (as reference data only) | Unverified as "current" pricing | Not used as a live source, just reference | **Use as reference only** — directionally useful for calibrating a synthetic fare model, not citable as a live price |
| India regulatory surge cap (0.5x–2x base fare) | N/A — public regulation | N/A | Yes (India-wide) | Yes — publicly available now | Verified (government guideline coverage) | None | **Use as the anchor for a synthetic cab-fare model** |
| **Meru Cabs "Exactometer"** (round 3) | Not an API — a feature of Meru's own consumer app | N/A | N/A | N/A | Verified (described in third-party coverage of Meru's own feature) | None | **Not a usable source, but corroborating evidence**: Meru's own real-world fixed-fare pricing is explicitly anchored to the State Transport Authority's prescribed fare — a second real-world confirmation that a regulatory-anchored synthetic model is the right approach, not a new data point |

### Bottom line across all three categories (updated after round 3)

| Category | Best real/sandbox option found | Realistic for this project? |
|---|---|---|
| Flights | Duffel test mode (now with Sabre Dev Studio as a credible second sandbox), supplemented by Travelpayouts' free Data API for real trend/baseline context | Partial — two real API contracts and a real trend signal, but no live point-quote anywhere; Skyscanner and direct Indian-carrier APIs now confirmed not to exist as free options, not just unfound |
| Hotels | **Hotelbeds self-serve evaluation key** remains the strongest candidate; RateHawk is a second possible option with conflicting access reports | **Worth directly registering for both and testing** — three research rounds in, these two are the only hotel options that aren't flatly partnership-gated |
| Cabs | No real fare-source candidate exists in any of three rounds; Google Routes API (distance) + regulatory surge band + Meru's own real-world pricing policy all point to the same synthetic approach | No — synthetic fare source required, now corroborated by a real operator's own pricing policy in addition to the regulatory anchor and real distance data |

**This is an evidenced finding from three full research passes, not an assumption or
a shortcut**: genuinely free, live, real-time access across all three categories, for
India routes, within a 7-day window, is not realistically available — confirmed
repeatedly, not just once. What three rounds of searching changed is the *quality* and
*certainty* of the fallback: flights now have two real sandbox contracts (Duffel,
Sabre) plus a real trend signal (Travelpayouts); hotels have two candidates worth
directly testing (Hotelbeds, RateHawk) instead of zero; and the cab leg, while still
sourceless for a live quote, is now backed by three independent real inputs (the
regulatory surge band, real distance/duration from Google's Routes API, and a real
operator's own fixed-fare pricing policy) rather than one invented range. This is
exactly what §04 asks for when a category is inaccessible — a documented, thoroughly
evidenced reason, not a shortcut around the requirement.

## 8. Open items

- **Concrete next actions, not yet done:** actually register for (a) the Hotelbeds
  evaluation key and (b) RateHawk's API program, and make real test calls against
  both, to resolve which — if either — gives usable hotel data and whether either's
  "test" content is real or synthetic. These are quick registration checks, not
  research questions, and are the two open items that could still change the hotel
  data-source decision.
- **Not yet decided (intentionally):** frontend framework, database, scheduler, final
  per-category data-source selection. These wait until the domain research above is
  considered complete — which, as of this document, it now is for all three
  categories (flights, hotels, cabs), across two full research passes.

---

*Full raw research (uncondensed, with every source link) lives in `docs/NOTES.md`.
The formal options-considered log for the Methodology Report lives in
`docs/DECISIONS.md`.*
