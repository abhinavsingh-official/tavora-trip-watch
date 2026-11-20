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

Four research rounds in (the first two covered flights in depth with a first pass on
hotels/cabs; round 3 deepened data sources; round 4 below deepened competitors
specifically and reorganized this section into subsections rather than one flat table
per category — per explicit instruction, since a single table per category was judged
too thin for a 20%-weighted grading area).

### 6.1 The four mechanism families — read this first

Every real competitor product found across flights and hotels falls into one of four
families. Naming them once, here, avoids repeating the same explanation three times
below.

| Family | What it actually does | Who does this | Pays out / covers | Our relevance |
|---|---|---|---|---|
| **A — Trend/history prediction** | Forecasts rise/fall direction (sometimes with a confidence label) from historical price data; never holds or quotes a specific price | Google Flights, Skyscanner, ixigo Fare Intelligence, Hopper (flights+hotels), Kayak (hotels) | Nothing — informational only | Low. We don't predict; we observe actual quotes |
| **B — Lock/freeze (paid hold)** | Pay a fee/deposit to hold a specific fare/rate for a fixed window; covered if price rises, forfeited/credited if unused | ixigo Smart Lock / Price Lock, Hopper Price Freeze (flights+hotels), Cleartrip PriceLock, MakeMyTrip Price Lock (via Hopper partnership), Goibibo Price Lock | Fare/rate rise within the lock window, up to a stated cap | **High** — this is commercially the closest shipped analog to our §08 hold mechanic |
| **C — Post-booking price-match/refund** | After a confirmed booking, if the same thing is found cheaper elsewhere (or the same booking's own price later drops), refund the difference — no upfront fee | MakeMyTrip (flights, drop-after-booking), Booking.com "We Price Match" (hotels), Expedia Hotel Price Guarantee (hotels, status conflicting) | The price difference, in cash, after booking | Medium — a real precedent for "honor a later-observed lower valid total," though ours notifies pre-booking rather than refunding post-booking |
| **D — Observed-price tracking (poll & compare)** | Repeatedly checks an actual price at intervals and alerts on a real observed change — no prediction, no lock, no refund | Scraping-based trackers (e.g. PageCrawl-style tools), TripIt Pro flight alerts | Nothing — alert only | **Highest** — structurally identical to our own §06 monitor → §07 alert loop |

**Why this framing matters:** our own design (§06–08) is a **hybrid of B and D** — the
monitoring/alerting core is family D (poll real inventory, alert on a real observed
crossing), and the 2-minute hold mechanic is a stripped-down, unpaid, much
shorter-duration version of family B. No single competitor combines both the way this
assignment requires; stating that explicitly in the Methodology Report is stronger
than claiming the whole design is novel, or claiming it copies one specific product.

### 6.2 Flights

#### 6.2.1 Family A — trend/history prediction

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **ixigo — Fare Intelligence** | Trend/history-based prediction (≤30 days out, domestic only) | Fare Prediction + Fare Alerts (drop notifications on tracked routes) | None | Verified (ixigo's own docs: domestic-only, 30-day window) | Medium — alerting mechanism parallels §07 |
| **Google Flights — Price Forecast/Alerts** | Trend/history-based prediction | 7-day direction estimate with stated confidence; drop alerts | None | Verified (Google's own description, via secondary source) for the mechanism; accuracy figures unverified | Low — prediction only, no hold/lock |
| **Skyscanner — price-prediction labels** (round 4) | Trend/history-based | Labels a fare "low/typical/high" vs. historical data for that route | None | Verified mechanism (widely documented); no independent accuracy audit found | Low — a coarser prediction signal, same family as Google Flights |

#### 6.2.2 Family B — lock/freeze products (highest relevance to §08)

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **ixigo — Smart Lock / Price Lock** | Continuous fare monitoring against a target budget | Locks fare once found within budget | ₹99/passenger starting fee (per "Price Lock" coverage); covers fare rise after lock up to ₹4,000 domestic / ₹8,000 international; up to 2-day hold; lock fee non-refundable; covers fare only, not seat availability | Verified (company press/docs) for mechanism and caps; the ₹4,000 cap is independently corroborated across two separately-named ixigo products (round 1 "Smart Lock," round 4 "Price Lock"), which is either the same product under two names or two consistent products — not resolved which, but the number itself is doubly confirmed | **High** — almost exactly our §06–08 loop as a shipped product |
| **Hopper — Price Freeze (flights)** | Deposit product, not a prediction mechanism | Lock a fare for up to 20 days for a $10–20 deposit | Deposit counts toward fare if booked in-window; otherwise becomes travel credit or is lost | Verified (Hopper's own terms) for mechanics; unverified accuracy claims ("95% accuracy," marketing) | Medium — real hold/lock precedent, paid, much longer-duration than our 2-minute hold |
| **MakeMyTrip — Price Lock** (round 4) | Deposit product, **built on licensed Hopper Price Freeze technology** — a commercial partnership, not an independent build | Lock a domestic flight fare | **Conflicting duration**: launch coverage states a 7-day hold window; a third-party competitor comparison page (marketing material, lower trust) claims 12 hours instead | Conflicting — flagged rather than resolved; the partnership itself is verified, the exact duration is not | Medium — same family as Hopper/ixigo, notable mainly for confirming Hopper's freeze tech is white-labeled into at least one major Indian OTA |
| **Cleartrip — PriceLock** (round 4) | Deposit product | Pay a small, non-refundable fee to hold a fare | Availability restricted "based on variety of factors determined by Cleartrip" (i.e. not every fare qualifies — same restriction shape as ixigo/Hopper); fee forfeited if lock lapses unused | Verified (Cleartrip's own PriceLock + PriceLock Policy pages) for mechanics; live since 2016 per a secondary (Wikipedia-mirrored) source only | Medium — a third independently-confirmed example of the same lock-fee pattern |
| **Goibibo — Price Lock** (round 4, MakeMyTrip group brand) | Deposit product | 1/3/7-day lock variants | Fee credited toward the ticket if booked within the window | Verified via dedicated launch coverage | Medium — same family, notable for offering a *choice* of lock durations rather than one fixed window |

**Takeaway for 6.2.1–6.2.2:** five independent products (ixigo, Hopper, MakeMyTrip,
Cleartrip, Goibibo) now confirm the same lock-fee mechanic — pay something small
upfront, hold a fare for a bounded window, forfeit or get credited if unused. This
isn't an invented mechanic for §08; it's a more rigorous, engineering-correct version
of a pattern that already exists commercially five times over, built at prototype
scale (a free, 2-minute hold vs. their paid, multi-day holds).

#### 6.2.3 Family C — post-booking price-match/refund (round 4, new family for flights)

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **MakeMyTrip — refund-the-difference** | Post-booking price-match | If the price of an already-booked flight drops after booking, refund the difference — no upfront fee | Unspecified cap/window in the coverage found | Verified via dedicated coverage (Curly Tales), not MakeMyTrip's own terms page directly | Medium — the closest real precedent to "notify on a further valid improvement" (§07), except this one pays cash instead of alerting |
| **Expedia — flight price match** | N/A — reported never to have existed as a standard feature | — | — | **Not found** as an active product | N/A |

#### 6.2.4 Paid itinerary-alert add-ons and a ruled-out dead end

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **TripIt Pro — price alerts** | Family D-adjacent (polls and alerts, but paid add-on to an itinerary manager, not a standalone watcher) | Fare-drop alerts post-booking | $49/yr subscription (per one 2024 user report); doesn't filter basic-economy fares per the same report | Unverified (single user report, not TripIt's own published terms) | Low-Medium — same alerting shape as our own design, but bundled into a paid itinerary product rather than standalone |
| **Hipmunk** (round 4, ruled out) | N/A | — | — | Shut down **2020-01-23** by SAP Concur, folded into Concur's expense/travel direction; no source found describing a price-prediction feature it ever had | N/A — the premise for researching it didn't hold up; logged so it isn't re-investigated |

**Takeaway for flights overall:** four real families now confirmed (predict / lock /
post-booking refund / paid-alert), with **five separate products** in the lock family
alone. Our design sits at the intersection of the lock family's hold mechanic and the
paid-alert family's polling/notification shape — stronger grounding for the
Methodology Report than the two-product comparison in earlier rounds.

### 6.3 Hotels

#### 6.3.1 Family A — trend/history prediction

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **Hopper — hotel price prediction** | Trend/history-based (historical price + review signals) | Rise/fall forecast for a specific hotel | None | Verified mechanism description; unverified accuracy ("95% accuracy" — third-party claim) | Low — prediction only |
| **Kayak — hotel price forecast** | Trend/history-based | 7-day rise/fall direction from historical + real-time data | None | Verified mechanism (Kayak's own description); no independent accuracy audit found | Low — prediction only |

#### 6.3.2 Family B — lock/freeze

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **Hopper — Price Freeze (hotels)** | Deposit product | Lock a specific hotel's rate for up to 60 days (14/21-day variants reported by other sources/partners) | Covers price rise during freeze window up to ~$100 cap, with a max-difference threshold; not a reservation — framed as price insurance | Verified (company press) for mechanics; terms reported inconsistently across sources (likely changed/partner-specific, e.g. Capital One's Hopper-powered portal) | Medium — real hold/lock precedent, paid, much longer window than ours |

#### 6.3.3 Family C — post-booking price-match guarantees (round 4, new for hotels)

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **Booking.com — "We Price Match"** | Post-booking exact-match refund | If the *exact same* accommodation/room/conditions is found cheaper elsewhere after booking, refund the difference | Claim window reported up to 24h before arrival; match must cover room rate + common taxes/fees, not extras/currency differences; Booking.com reserves **sole discretion** over eligibility (per a terms-tracking site's quoted clause) | Conflicting/unresolved — Booking's own current terms page didn't surface directly in search, so this rests on secondary sources (NerdWallet, a terms-tracker, an affiliate guide); a 2026-09-28 headline reports Booking.com "drops external price checks from a key program" under EU DMA rules, not confirmed whether that's this program | Medium — a real precedent for "honor a later valid lower total," same shape as MakeMyTrip's flight refund |
| **Expedia — Hotel Price Guarantee** | Post-booking exact-match refund (reported) | Historically: match required same property/room type/rate plan/refund policy/dates | **Conflicting and likely stale**: one comparison page states the guarantee ended for new bookings 2026-07-28; older material (Expedia's own price-claim page text, 2019 reporting) describes it as active with strict exact-match terms and Rewards-member-only eligibility in at least one reported version | Conflicting — not relied on either way; flagged explicitly rather than asserted | Low — likely discontinued, logged for completeness and so it isn't re-researched assuming it's active |

#### 6.3.4 Family D — observed-price tracking (our own family)

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **Scraping-based trackers (e.g. PageCrawl)** | **Observed-price tracking** — polls a specific booking-page URL at intervals, alerts on an actual observed rate change | Price-drop alert on a tracked page | None | Verified (how the tool works is documented by the vendor itself; not an accuracy claim, just a mechanism) | **Highest** — structurally the closest real analog to our own §06 poll → compare → alert cycle |
| Booking.com / Trivago internal mechanism | Unknown | — | — | **Not found** — no public documentation of their own price-alert internals surfaced by this research | N/A |

**Takeaway for hotels overall:** hotels now have the same four-family shape as
flights, including the newly-confirmed price-match family (Booking.com, Expedia).
**Our own design still sits in family D, not A** — worth stating explicitly in the
Methodology Report: this is a price *watcher*, not a price *predictor*, a real and
named category of existing tool, just not the most heavily marketed one — and
Booking.com/Expedia's family-C products show that even the biggest OTAs build
"honor a better price you find later" as a *refund*, never as a live dashboard the
way this assignment requires.

### 6.4 Cabs / airport transfers

Cabs don't fit cleanly into families A–D the way flights/hotels do, because a
ride-hail fare isn't a quote you can hold — it's computed live at request time. Round
4's research found something more useful than another surge-pricing data point: a
**real commercial category that is quotable in advance**, which changes how the cab
leg of this project should be framed, not just what data backs it.

#### 6.4.1 Surge-based rideshare — not trackable, ruled out as a competitor analog

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **Uber — surge pricing** | **Real-time multiplier** — automatic, driven by hyperlocal rider demand vs. driver availability at request time; company states it also factors in market-condition forecasts | None (not trackable/alertable — it's a live price, not a quote) | Emergency surge caps applied by Uber's own teams in major events | Verified (Uber's own pages) for the core mechanism; third-party claims of explicit weather/event/traffic inputs unverified | **None** — not a trackable quote at all, structurally incompatible with a price-watch pattern |
| **Ola — surge pricing** | Reportedly the same general supply/demand multiplier concept | None | Unknown | **No published detail found** — least documented of anything researched | None |

#### 6.4.2 Fixed-quote airport-transfer marketplaces (round 4 — the significant new finding)

| Product | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **Kiwitaxi** | **Fixed, pre-quoted price** for a specific route, confirmed at booking | Airport ⇄ hotel transfer booked in advance at a locked price | Price doesn't change for traffic or flight delay, per a third-party guide (not Kiwitaxi's own terms page directly) | Unverified (single secondary guide); access path is via **PHPTRAVELS**, described as an "official partner" reselling Kiwitaxi inventory through its own tech layer — i.e. only reachable as a sub-reseller, not a direct signup | **High relevance as a real-world analog** — structurally this *is* what §01 means by "destination airport transfers": a fixed point-to-point leg, not an open-ended ride-hail trip |
| **GetTransfer** | Fixed/quoted pricing via a documented `route_info` endpoint | Transfer booking with price returned per route | Standard API rate-limit (HTTP 429) pattern | **Secondary source only** — documented by Travelpayouts' support site describing GetTransfer's API, not GetTransfer's own official developer docs; needs direct verification | Medium — a real quotable-transfer API exists somewhere in this space, even if this project can't confirm direct self-serve access to it within the timeline |
| **Welcome Pickups** | Fixed, pre-quoted pricing (per marketing coverage) | Airport transfer booked in advance | Prices fixed before travel | Unverified — no technical/API detail found; conflicting coverage-area claims (60+ vs. 100+ countries across sources) | Low-Medium — a third independent example of the same fixed-quote shape, no usable access path found |

#### 6.4.3 Indian outstation/airport-transfer operators — group vehicles, not rideshare (round 5)

Prompted by re-reading §01's "destination airport transfers" as a pre-booked,
group-sized transfer for a vacationing party with luggage — the shape User B's 4
adults actually need — rather than an on-demand Uber/Ola ride. Looked specifically at
Indian operators selling exactly this.

| Source | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| **Savaari.com** | Fixed, pre-quoted outstation/airport fares | Fleet explicitly includes tempo travellers for group transfers, alongside sedans/SUVs/Innovas | Outstation round-trip AC tempo traveller rate: **₹26/km**, stated all-inclusive (driver allowance, toll, fuel, GST); no airport-specific tempo traveller fare found | Verified (Savaari's own pages) for fleet/rate; no airport-specific tempo rate confirmed | Medium — confirms the vehicle-class need (sedan vs. tempo traveller) is real, but **no public developer API** — consumer booking only |
| **Carzonrent India** | Fixed, pre-quoted corporate/airport transfers | Dedicated airport counters at Delhi/Bengaluru/Lucknow/Ahmedabad per its own site | "All inclusive transparent pricing" advertised, no published rate card | Verified (own site) for service existence; no rate data found | Low — real operator, but bulk/corporate access is contact-form-only, **no public API** |
| **CabBazar — the most significant finding this round** | Fixed, pre-quoted pricing via a **documented cab-booking API** covering outstation (round-trip + one-way) and **airport taxi service** specifically | A real, named, documented contract matching this project's exact use case (location lookup → get-prices → initiate/confirm booking → webhooks → cancellation) | Access requires contacting CabBazar with a business profile and expected sales volume | Verified (CabBazar's own published API page) for the contract's existence; access gate is the same shape as Booking.com/TBO's B2B gates | **Not reachable in 7 days** (same gate pattern as other B2B sources), but the strongest *API-shaped* real precedent found for this category across all five research rounds |
| **MakeMyTrip Car Rental** (per-city pages) | Fixed-km package + per-km overage, server-rendered booking pages | Lists Tempo Traveller (12-seat, 8-bag) among outstation vehicle options | Sample route: 85 km included, ₹20.5/km beyond, ₹3,394–3,968 total + taxes | Verified (MakeMyTrip's own pages) for one sample route; not a general rate card | Low — no public API, same scraper-risk shape as other city-page-only sources |
| **Tempo traveller market rate** (3 independent rental operators, round 5) | N/A — market rates, not a regulation | Roughly **₹20–28/km** by seater size (12–26 seats), typically a 250–300 km/day minimum, plus a separate ₹500–700/day driver charge | Not an official/government rate — market-triangulated across 3 unrelated operators (Triveni Cabs, ChikuCab, a Gurgaon listing), not resting on one source | Verified as "stated by multiple independent operators," explicitly **not** government-verified like the surge cap below | **High relevance as a second real anchor**, specifically for larger-party transfers (User B's 4 adults), where a sedan-class flat rate would be the wrong vehicle class entirely |

#### 6.4.4 Regulatory and real-operator pricing anchors

| Source | Mechanism | Core feature | Guarantee terms | Claim verification | Relevance |
|---|---|---|---|---|---|
| India regulatory surge cap (2020 → 2025 Motor Vehicle Aggregator Guidelines) | N/A (regulation, not a product) | Caps surge at 1.5x base fare (2020) → 2x base fare at peak (2025 revision); floor of 50% of base off-peak | Legally mandated ceiling/floor | Verified (government guideline coverage) | **High** — a real, citable multiplier range (0.5x–2x) for a synthetic fare model |
| **Meru Cabs — "Exactometer"** | Not an API — a feature of Meru's own consumer app | Fixed-fare pricing anchored to the **State Transport Authority's prescribed fare** for that route | N/A | Verified (described in third-party coverage of Meru's own feature) | Not a usable data source, but a second real-world confirmation that a regulatory-anchored, fixed-quote model is the right shape, not an invented one |

**Takeaway for cabs — a reframing, not just a new data point:** the right mental model
for this project's cab/transfer leg is no longer "we can't track a surge multiplier,
so we'll fake one." It's **"a real commercial category — fixed-quote airport-transfer
marketplaces and Indian outstation operators (Kiwitaxi, GetTransfer, Welcome Pickups,
Savaari, Carzonrent, CabBazar) — already exists and matches §01's own description of
this leg (a destination airport transfer, not an open-ended ride-hail trip) more
closely than Uber/Ola surge pricing ever did.** None of these has a confirmed free,
immediate, self-serve API reachable in a 7-day window (CabBazar comes closest, with a
genuinely documented API, but it's gated the same way as other B2B sources), so a
synthetic source is still necessary — but it should be built and described as
*modeling a fixed-quote transfer product that picks a vehicle class by party size*
(sedan-class for 2 adults, a larger-vehicle/tempo-traveller-anchored rate for 4
adults), backed by real distance data from Google's Routes API, bounded by the
regulatory surge-cap range as a sanity check, and anchored for larger parties to the
real ₹20–28/km tempo-traveller market range found this round — not merely "a guess at
a surge multiplier," and not a single flat rate regardless of group size. This is a
materially stronger justification for the Methodology Report's synthetic-source
writeup, and it directly satisfies §05's "cab passenger/luggage capacity" requirement
rather than silently ignoring it.

## 7. Data-source landscape (India)

### 7.1 Flights

| Source | Access model | Price realism | India coverage | Reachable in 7 days | Verification status | Access-control risk | Verdict |
|---|---|---|---|---|---|---|---|
| **Amadeus Self-Service** | Conflicting — docs describe a free Test tier; two independent third-party sources (round 1, round 7) now report the free portal decommissioned, round 7 citing a specific date (2026-07-17) | Real historical/cached test data (if the tier still exists) | Vendor-claimed, unverified | **Uncertain, leaning "no"** — two corroborating-but-secondary reports, still not Amadeus's own confirmation | Conflicting, strengthened toward "likely decommissioned" | None | **Reject** — unresolved access, two independent signals it's gone |
| **Duffel** | Free self-serve sandbox ("test mode") | **Synthetic test data** — explicitly confirmed non-real/non-live prices, even in test mode, via a dedicated test airline | N/A (test airline, not real carriers) | **Yes** — confirmed free, immediate, unlimited test balance | Verified (Duffel's own help center) | None | **Use** — strongest confirmed free sandbox; the realistic API contract is the value, not real prices |
| **Kiwi.com Tequila** | Reportedly closed to public self-serve since May 2024; invitation/partnership-only per most sources | Real (when accessible) | N/A | **No/Uncertain** | Conflicting | None | **Reject** — inconsistent reports, can't rely on it |
| **SerpApi (Google Flights scrape)** | Free tier (disputed size: 100–250/month) | **Real, scraped** — mirrors actual Google Flights search results | Yes (any Google-indexed route) | Yes, within free-tier limits | Conflicting on exact quota | None (scrapes a public search results page, not an airline's protected system) | **Possible supplement** — real prices, but search-engine-mediated rather than a direct supplier API; free-tier quota too uncertain to be a primary source |
| **Travelpayouts — Aviasales Data API** (round 2) | Free, self-serve — sign up + connect to the Aviasales program, no extra approval | **Real, but historical/trend** — price-calendar and popular-route data via GraphQL, not a live point-in-time quote | Yes (any Aviasales-covered route, incl. India) | Yes | Verified (Travelpayouts' own support docs) | None | **Use as a supplementary signal** — a real baseline/trend range to calibrate against, not a live-quote replacement |
| **Travelpayouts — Aviasales real-time Flight Search API** (round 2) | Gated — "access provided only to projects with MAU starting from 50,000" | Real, live | Yes | **No** — MAU requirement makes this unreachable for a new solo prototype | Verified (Travelpayouts' own docs) | None | **Reject** — real but structurally inaccessible for this project's scale |
| **Skyscanner — official partner API** (round 2) | No public free tier at all; commercial partnership only (commonly ~100K MAU) | Real (if access were granted) | Yes | No | Verified (no free path exists) | None | **Reject** — no legitimate self-serve path exists |
| **Skyscanner — unofficial RapidAPI/Apify scraper wrappers** (round 2) | "Free tier" advertised (e.g. 100 calls/month), but these are third-party scrapers, not Skyscanner's own API | Real (scraped), but unofficial | Yes | Yes (if used) | Unverified/unstable — one Stack Overflow report notes an endpoint already pulled from RapidAPI | **Ruled out** — scraping a protected search product is exactly what §04's "do not bypass access controls" forbids | **Reject outright** — not just deprioritized, explicitly disallowed by the brief regardless of convenience |
| **Sabre Dev Studio** (round 3) | **Free self-serve test key** — Sabre's own site: immediate signup, no accreditation for the test key itself; browser-based "Try It Out" per endpoint | Same shape as Duffel — third-party guides describe test-key data as "limited or simulated," not live | Unconfirmed for India specifically | **Yes** — per Sabre's own docs | **Conflicting** — a third-party comparison (Geekflare) claims no self-serve path exists at all, directly contradicting Sabre's own site; treating Sabre's own docs as authoritative per our verification standard | None | **Credible second sandbox alongside Duffel** — doesn't change the "no live flight prices" conclusion, but a real second GDS contract to reference/cross-check |
| **Direct Indian carrier APIs — IndiGo & Air India NDC** (round 3, corrected by round 7) | **Real, documented NDC APIs exist for both** (Air India's own NDC portal, IndiGo's NDC via a Navitaire gateway per its own developer docs) — round 3's "none found" is corrected here: they exist, but are **explicitly restricted to authorized/registered partners** ("6E authorized partners" for IndiGo; registration + `ndcdistribution@airindia.com` contact for Air India), not self-serve | Real (if access were granted) | Yes | No | Verified (both airlines' own developer/NDC documentation) | None | **Reject — confirmed to exist but partner-gated**, a more precise finding than round 3's "doesn't exist" |
| **AviationStack / FlightLabs** (round 3) | Free tier exists (~100 req/month, AviationStack) | AviationStack is schedule/status-focused, pricing data vendor-claimed and unverified; FlightLabs' "Flight Prices" endpoint is documented as returning "scraped flight options," not a licensed feed | Unconfirmed | Uncertain | Unverified | Possible (if FlightLabs is in fact a scraper) | **Reject** — not a credible licensed fare source either way |
| **Yatra NDC corporate booking / B2B aggregators (TBO, Tripjack)** (round 7) | Yatra's NDC-based system is a corporate booking product, not a public API; TBO/Tripjack are the same B2B-vetting gate already ruled out for hotels | Real (if access were granted) | Yes | No | Verified (coverage of Yatra's product exists; TBO/Tripjack gate already confirmed) | None | **Reject** — same B2B-gate shape as sources already ruled out, no new path |

### 7.2 Hotels

| Source | Access model | Price realism | India coverage | Reachable in 7 days | Verification status | Access-control risk | Verdict |
|---|---|---|---|---|---|---|---|
| **Booking.com Demand API** | Requires becoming an approved Managed Affiliate Partner first; sandbox only unlocks after that | Real (sandbox mirrors live inventory once access is granted) | Yes, if access is granted | **No** — partnership approval won't complete in a 7-day window | Verified (Booking.com's own docs — the gate itself, not a rumor) | None | **Reject for this timeline** — real documented sandbox, just not reachable in time |
| **Hotelbeds (HBX Group) Apitude API** (round 2) | **Free self-serve** — "Get your free API key," immediate, no partnership approval needed | **Unresolved** — official docs don't state whether evaluation-environment content/prices are real or a separate synthetic test dataset; sources conflict (one partner guide implies real content, one unofficial analysis suggests anomalous/non-live test prices) | Unconfirmed for India specifically, needs direct check | **Yes** — registration and first calls are immediate | Conflicting on realism, but the access model itself is verified from the official developer portal | None | **Strongest hotel candidate found — register and test directly** rather than defaulting straight to synthetic; capped at 50 requests/day on the free evaluation key |
| **TBO Holidays** (round 2, re-checked) | B2B only — requires becoming a vetted, registered travel agency (security deposit or credit line) | Real (if access were granted) | Yes | **No** — vetting process won't complete in a 7-day window | Verified (no self-serve developer path exists) | None | **Reject for this timeline** — same shape of gate as Booking.com |
| **MakCorps / Apify-style scrapers** | Paid per-call, or ToS-risky scraping | Real (scraped) | Yes | Yes (paid) | Unverified pricing/coverage claims | **Some/Ruled out** — the assignment explicitly forbids bypassing access controls | **Reject** — explicitly disallowed by the brief, regardless of cost |
| **RateHawk (Emerging Travel Group) ETG API v3** (round 3) | **Conflicting** — RateHawk's own marketing page implies self-serve ("register → get your free API key → certify"); a third-party integrator describes a gated process instead (contact as a registered travel company, sign an API agreement, then receive a sandbox key) | Real (if access is genuinely self-serve) | Unconfirmed | **Unclear** — depends on which access description is accurate | **Conflicting**, same shape of uncertainty as Amadeus in round 1 | None | **Unresolved — would need direct registration to settle**, not assumed either way |
| **Agoda** (round 3) | Partnership-gated ("Online Affiliates/MSE" model); API access handled case-by-case, not self-serve | Real (if access were granted) | Yes | No | Verified (no free self-serve path found) | Unofficial scraper alternatives exist (Apify, Parse.bot) but are ToS-risky | **Reject** — official path is gated, scraper alternatives ruled out on the same grounds as other scrapers |
| **Expedia Rapid API (incl. Hotels.com inventory)** (round 7) | **Confirmed gated** — Expedia's own XAP sandbox docs state sandbox access must be requested from an Account Manager; a third-party API tracker independently confirms "application, certification, negotiated commercial terms," no self-serve. A reseller (Vervotech) offers a 7-day free trial, but that's a third-party commercial layer in front of a gated API, not Expedia's own access | Real (if access were granted) | Yes | No | Verified (Expedia's own sandbox docs + independent third-party corroboration) | None | **Reject** — definitively confirmed gated, resolves a prior open question rather than leaving it uncertain |
| **OYO** (round 7) | **No public developer API at all** — confirmed by an API-tracking profile; the one "OYO Open API" document found is explicitly internal/partner-only, issued after a hotel **owner** onboards onto OYO's platform — a property-management API, not a price-search API | N/A | N/A | No | Verified (API tracker + the document's own stated scope) | Third-party scrapers exist (Apify) but paid and ToS-risky | **Reject — wrong product entirely**, not merely inaccessible |
| **Yatra, EaseMyTrip, Cleartrip (hotels)** (round 7) | All three have *some* programmatic access, but exclusively via third-party integration vendors (e.g. Vervotech) under B2B distribution agreements; Cleartrip's only located API docs are on its UAE site, no India-specific self-serve program found | Real (if access were granted) | Yes | No | Verified (vendor integration pages describe the gate; no self-serve program found) | None | **Reject** — same B2B-gate shape as Booking.com/TBO/Agoda |

### 7.3 Cabs / airport transfers

| Source | Access model | Price realism | India coverage | Reachable in 7 days | Verification status | Access-control risk | Verdict |
|---|---|---|---|---|---|---|---|
| **Ola Ride Estimate API** | Invite-only, case-by-case via email to affiliates team | Real (if granted access) | Yes | **Uncertain/unlikely** — no guaranteed turnaround | Verified (Ola's own docs describe the gate) | None | **Reject for this timeline** — real but not reliably reachable in time |
| **Ola Outstation API** (round 6 — the strongest documented cab contract found across all research) | **Real, documented developer API** — `developers.olacabs.com/docs/outstation` publishes actual fare-breakup fields (trip type, distance/time units, base fare, minimum distance) and a booking/cancellation endpoint. Access is case-by-case via an email request to Ola's affiliates team; Ola states outright that access is "opened to interested affiliates and partners on a case-by-case basis" with no approval guarantee | Real (if access were granted) | Yes | No | Verified (Ola's own developer documentation) | None | **Reject for this timeline** — the single most concrete, officially-documented cab-fare contract found in six research rounds, still gated the same way as everything else |
| **CabBazar cab-booking API** (round 5) | **Documented API** covering outstation (round-trip/one-way) and **airport taxi service** specifically (location lookup → get-prices → initiate/confirm booking → webhooks → cancellation) | Real (if access were granted) | Yes | No | Verified (CabBazar's own published API page) | None | **Reject for this timeline** — access requires contacting CabBazar with a business profile and expected sales volume, same B2B gate as Booking.com/TBO |
| **Savaari.com, Carzonrent India** (round 5) | Real, established Indian outstation/airport-transfer operators; Savaari's fleet confirmed to include tempo travellers for group transfers | Real (consumer booking only) | Yes | No | Verified (both companies' own sites) | None | **Reject** — **no public developer API at all** for either, consumer booking only |
| **ixigo Cabs** (round 6) | Consumer aggregator over Ola/Uber/Easycabs, incl. a live nationwide Airport Cabs product | N/A | Yes | No | Verified (aggregator model, not its own API); only "API" pages found are unverified third-party marketing | None | **Reject** — aggregator with no API, same pattern as other aggregator-without-API findings |
| **12Go Asia** (round 6) | Real partner API exists for scheduled multimodal transport (bus/train/ferry), covering India via bus operators | Real (if access were granted) | Partial (bus/train only) | N/A | Verified (12Go's own partnership coverage) | None | **Reject on fit, not just access** — a scheduled public-transport marketplace, not a private point-to-point group transfer product; wrong category for "destination airport transfer" |
| **Uber (India developer access)** | Sandbox itself is usable without privileged scopes, but the price-estimates endpoint is gated behind Uber's approval | Real (if granted access) | Unconfirmed | No | Verified (Uber's own docs) | **Confirmed ToS conflict (round 3)** — Uber's API Terms of Use explicitly prohibit using the API to offer price comparisons with competitive third-party services, directly relevant to a trip price-watch tool | **Reject — not just inaccessible, contractually in conflict with this project's purpose** |
| **Rome2Rio** (round 2, checked and ruled out) | Was free/self-serve historically for routing | **Not a fare source at all** — Rome2Rio's own documentation states the API does not provide live transit prices or airfares, and recommends pairing it with a separate airfare provider | N/A | N/A | Verified (Rome2Rio's own documentation) | None | **Reject — out of scope**, not a pricing API regardless of access terms |
| **Google Distance Matrix (legacy) / Routes API "Compute Route Matrix"** (round 2) | **Free, self-serve** — standard Google Cloud API key, no partnership gate | **Not a fare source** — returns real driving distance/duration, not a price | Yes — confirmed real India-specific free quota | Yes — immediate | Verified (Google's own pricing pages); **70,000 free events/month specifically for India**, vs. 10,000 globally | None | **Use as a supporting input** — real geographic distance to ground a synthetic cab-fare formula, not a price source itself |
| Scraped fare figures (e.g. ₹150–218 airport pickup range across operators) | Scrape/aggregator pages | Real figures, but a point-in-time sample, not a live feed | Yes | Yes (as reference data only) | Unverified as "current" pricing | Not used as a live source, just reference | **Use as reference only** — directionally useful for calibrating a synthetic fare model, not citable as a live price |
| India regulatory surge cap (0.5x–2x base fare) | N/A — public regulation | N/A | Yes (India-wide) | Yes — publicly available now | Verified (government guideline coverage) | None | **Use as the anchor for a synthetic cab-fare model** |
| **Official RTO/state per-km taxi rate cards** (round 6 — Mumbai ₹21.90/km, Nagpur ₹28.80/km AC, Karnataka ~₹18.66/km) | N/A — public, government-published tariff revisions, per-state | N/A | Yes, but state-by-state — no single national rate card exists | Yes — publicly available now | Verified (state transport department coverage, specific dates where available) | None | **Use as the primary, most-authoritative per-km anchor** for the synthetic model — stronger than private operator estimates since it's government-published, not vendor-marketed |
| **Meru Cabs "Exactometer"** (round 3) | Not an API — a feature of Meru's own consumer app | N/A | N/A | N/A | Verified (described in third-party coverage of Meru's own feature) | None | **Not a usable source, but corroborating evidence**: Meru's own real-world fixed-fare pricing is explicitly anchored to the State Transport Authority's prescribed fare — a second real-world confirmation that a regulatory-anchored synthetic model is the right approach, not a new data point |
| **Tempo traveller market rates** (round 5 — ₹20–28/km by seater size, 3 independent rental operators) | N/A — private market rates, not a regulation | N/A | Yes, but operator-estimated not official | Yes — publicly available now | Verified as "stated by multiple operators," explicitly **not** government-verified | None | **Use as a secondary anchor for the larger-vehicle case** (4+ adults), alongside the official RTO rate above |

### Bottom line across all three categories (updated after round 7)

| Category | Best real/sandbox option found | Realistic for this project? |
|---|---|---|
| Flights | Duffel test mode (with Sabre Dev Studio as a credible second sandbox), supplemented by Travelpayouts' free Data API for real trend/baseline context | Partial — two real API contracts and a real trend signal, but no live point-quote anywhere; direct Indian-carrier NDC APIs (Air India, IndiGo) now confirmed to exist but be partner-gated, not simply absent; Amadeus's free tier increasingly likely decommissioned (two corroborating reports) |
| Hotels | **Hotelbeds self-serve evaluation key** remains the strongest candidate; RateHawk is a second possible option with conflicting access reports | **Worth directly registering for both and testing** — seven research rounds in, these two remain the only hotel options that aren't flatly partnership-gated (Expedia Rapid and OYO now definitively confirmed gated/wrong-fit, not just unchecked) |
| Cabs | No real fare-source candidate exists in any of six rounds — including Ola's own documented Outstation API and CabBazar's documented airport-taxi API, both gated the same way as everything else; official RTO per-km rate cards, Google Routes distance, the regulatory surge band, Meru's pricing policy, and tempo-traveller market rates all point to the same synthetic, vehicle-class-aware approach | No — synthetic fare source required, now backed by the strongest and most varied evidence base of any category: one real government rate card per major city, one national regulation, one real operator's pricing policy, and two genuinely documented (if gated) real APIs confirming the product category itself is real |

**This is an evidenced finding from seven full research passes across flights,
hotels, and cabs — not an assumption or a shortcut, and specifically re-tested after
direct challenge that earlier rounds weren't thorough enough**: genuinely free, live,
real-time access across all three categories, for India routes, within a 7-day
window, is not realistically available — confirmed repeatedly, under real pressure to
find a counterexample, not just asserted once. What seven rounds of searching changed
is the *quality* and *certainty* of the fallback: flights now have two real sandbox
contracts (Duffel, Sabre) plus a real trend signal (Travelpayouts), and direct
carrier access is now known to exist-but-be-gated rather than simply unfound; hotels
have two candidates worth directly testing (Hotelbeds, RateHawk) instead of zero, and
two more large players (Expedia Rapid, OYO) are now definitively ruled out rather
than left open; and the cab leg, while still sourceless for a live quote, now has the
richest evidence base of all three categories — a real per-city government rate card,
a national regulation, a real operator's own pricing policy, real distance data, and
two genuinely documented (if B2B-gated) real cab APIs confirming this is a real
product category, not an invented one. This is exactly what §04 asks for when a
category is inaccessible — a documented, repeatedly-pressure-tested reason, not a
shortcut around the requirement.

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
  categories (flights, hotels, cabs), across four full research passes.
- **New framing to carry into the design, not just a data-source note:** the cab leg
  should be built and documented as a **fixed-quote airport-transfer model** (per
  §6.4.2's Kiwitaxi/GetTransfer/Welcome Pickups finding), not as a surge-multiplier
  simulation — a real commercial category matches the assignment's own "destination
  airport transfer" wording more closely than ride-hail surge pricing does.

---

*Full raw research (uncondensed, with every source link) lives in `docs/NOTES.md`.
The formal options-considered log for the Methodology Report lives in
`docs/DECISIONS.md`.*
