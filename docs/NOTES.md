# Notes

Running log of major decisions and findings as we work through this, in the order we
hit them. (`docs/DECISIONS.md` holds the more formal options-considered write-up for
the eventual Methodology Report; this file is the working log underneath it.)

---

## 2026-11-19 — Tavora's real site (tavora.in), for context only

Looked at two pages on the actual Tavora site to understand their real product and UI
patterns — explicitly NOT to clone, just to see how they think about this problem.

**`/plan` (browse/discovery page)**:
- A trip-discovery listing: "Where / When / Who" filter bar, cards grouped by state,
  each card = place name, duration, tag line, "from ₹X per person" price, 4-image
  collage. 52 results + "pair" combo cards (two places in one trip).
- Price framing: "Every price is per person, all in... the overnight bus or train, the
  stay and the rides there" — i.e. they *do* think in the same three components our
  assignment cares about (transport / stay / local transfer), just bundled into one
  "from" number on the listing page.
- **No price-watch, alert, or notify-me feature anywhere on this page.**
- Trust signals: "Checked by real people", "Can't book? Full refund", WhatsApp support.

**`/trip/{slug}` (a specific trip's detail page, e.g. Manali)**:
- Not a single page — a **6-step wizard**: Travel → Ride → Stay → Extras → Return →
  Review. Step 1 ("Getting there") shows car options priced individually (e.g.
  "₹17,150 for the car / ₹8,580 per person"), bus prices hidden until you pick one
  ("Pick a bus to see your price").
- Each step's footer: **"we confirm the live price before you pay."** This is their
  own version of our assignment's Section 08 (revalidate + fresh consent before
  booking) — a real precedent that this pattern (don't trust an old quote, recheck
  before purchase) is exactly how the real industry does it, not an invented
  requirement.
- No price-watch/alert feature visible here either — confirms the feature we're
  building doesn't exist on their real product. This assignment is testing whether we
  can design a genuinely new capability, not re-implement something they already ship.
- Other UI patterns worth borrowing conceptually (not visually): per-leg "Leave on"
  date picker, an explicit opt-out ("I'll get there on my own"), sort/filter on options,
  a loading state with real copy ("Checking trains, buses and rooms for your dates…")
  rather than a bare spinner.

**Takeaway for our design**: our "offer review" screen (assignment §08/§10) should
look and talk like their step-5 "Review" — a live revalidation moment with plain-
language status, not a generic confirmation dialog. Our three price components
(flight, stay, cab) match how Tavora itself frames pricing, which is a good sign the
assignment's model lines up with how this company actually thinks about trips.

### Full raw findings — `/plan` (browse/discovery page)

Fetched `https://tavora.in/plan`, HTTP 200, no login wall (header has a "Sign in" link
to `/sign-in?next=/plan` but the page itself is public). Extraction was flattened
markdown, so control types (dropdown vs. text field), colors, and fonts aren't visible
— everything below is from page text/structure only.

- **Scope of this page**: a browse/listing page ("Weekend trips from Delhi with
  prices"), not a single-trip flow. No price-watch, alert, booking form, or checkout
  on this page.
- **H1 / intro**: "Weekend trips." Tavora "plans and books weekend trips from Delhi
  NCR"; "Pick your dates and your group; real people check every part before you pay,
  and if we can't book it you get a full refund."
- **Top controls**: "Where" field (placeholder "Search places or a vibe"), a summary
  line "This weekend · 2 people". An "Your answers" section shows two editable-looking
  chips: "When: This weekend", "Who: 2 people".
- **Results**: "52 places fit you", grouped by state — Himachal Pradesh (21),
  Uttarakhand (16), Rajasthan (11), Others (4) — summing to 52, plus separate "pair"
  cards (two places combined, e.g. "Kasol + Tosh", "Jibhi + Tirthan Valley", labelled
  "Two places, one trip").
- **Card anatomy**: 4-image collage (1 main + 3 thumbnails), a tag line (seen: "Mountains
  this weekend", "Offbeat this weekend", "Among the cheapest", "Needs a long weekend"),
  name as H3, duration line ("2 days · 1 night"), "from ₹X per person" price line.
  Observed prices range ₹1,999 (Rishikesh, Mandawa) to ₹14,999 (Mukteshwar); Manali
  ₹3,499, Shimla ₹2,499, Jaisalmer ₹2,499, Nainital ₹9,499.
- **Each card links to** `/trip/{slug}?w={date_range}&n={people}&t={tier}` — e.g.
  `/trip/manali?w=2026-11-20_2026-11-22&n=2&t=comfort`. Every card on this page carries
  `t=comfort`; no other tier value observed. Pair cards add a `pair=` param (e.g.
  `pair=tosh`).
- **Price framing (explicit quote from the page)**: "Every price is per person, all
  in, for this weekend's dates: the overnight bus or train, the stay and the rides
  there." — i.e. Tavora already decomposes a trip into transport + stay + local rides,
  same three components our assignment cares about, just shown as one bundled "from"
  number at the listing level.
- **"Build your own"** card → `/custom` ("Your towns · your nights"), suggests
  Mussoorie, Shimla, Kufri.
- **Trust strip**: "Checked by real people" (`/how-it-works`), "Can't book? Full
  refund" (`/refunds`), "WhatsApp 9 am – 2 am" (WhatsApp link). Notice: "Trips and
  services currently start from Delhi NCR."
- **Reviews**: "4.9 from 9 reviews", quote cards mentioning the "trip support" team and
  a ₹1,000 discount promo.
- **Promo strip**: "AAHWAAN 2026 · Claim up to ₹1,000 off" (`/aahwaan`), repeated
  mid-page.
- **Header nav**: Find trips, Buses, Cars, Stays, Things to do, Offers, My trips,
  Corporate Offsites, Reviews, plus a Menu drawer. Mobile banner pushes "add to home
  screen" (PWA-style).
- **Footer**: site nav links, hotel partner logos (goSTOPS, Zostel, The Hosteller),
  support partner logos (Sarvam, Neon).
- **No sort/filter/budget-range control is visible anywhere on this page** — notable
  given our assignment explicitly requires max-stops, min-star-category, baggage
  filters on the request form. Tavora's own discovery UI is much coarser than what
  we're asked to build.
- Pages not fetched in this pass: `/custom`, `/how-it-works`, `/refunds`, `/trips`.

### Full raw findings — `/trip/manali` (a specific trip detail page)

Fetched `https://tavora.in/trip/manali?w=2026-11-20_2026-11-22&n=2&t=comfort`, HTTP
200, no login wall, no redirect, ~6.7k characters. The fetch is a model-extracted
summary of the page, not verbatim text, and the page is clearly client-side-rendered
in parts (loading placeholders appeared: "Checking trains, buses and rooms for your
dates…", "Finding buses and seats…"), so some content (e.g. the actual bus list) may
not have finished loading in the capture.

- **Not a single page — a 6-step wizard**: *Travel → Ride → Stay → Extras → Return →
  Review*, shown as a step progress indicator with the current step labelled ("Step 1
  of 6: Getting there").
- **Step 1 ("Getting there") content**:
  - A "Leave on" date selector (seen: "Fri 20 Nov", "Sat 21 Nov").
  - An explicit opt-out: "I'll get there on my own" ("Leave this journey out of your
    price") — i.e. any transport leg can be excluded from the computed total, not just
    chosen between options.
  - "Pick a bus" section with sort ("Price: low to high") and an "All filters" button;
    no actual bus options rendered in this capture (likely still loading).
  - Car options each showed: vehicle image, name ("Hatchback", "Wagon R or similar"),
    seat count + AC, "Included / Not included / Cancellation" tags, and two fare
    modes: "One way ₹9,360 — Drop only" vs. "Round trip ₹17,150 — Car stays 3 days".
    Per-person math shown alongside the car total, e.g. Hatchback "₹17,150 for the
    car / ₹8,580 per person"; Sedan "₹17,400 / ₹8,700 per person"; SUV "₹20,770 /
    ₹10,390 per person".
  - Bus price itself is hidden until you pick one: "Pick a bus to see your price" —
    i.e. they don't show a price for an unselected/ambiguous option, consistent with
    our assignment's "unknown required charges must not silently become zero."
- **Price breakdown overall**: no running total or full component-by-component
  breakdown is shown anywhere in this capture — pricing accumulates step by step as you
  make choices, not shown upfront as one itemized total. (Our assignment explicitly
  *does* require an upfront itemized breakdown for the whole package — this is a place
  our requirement is stricter than what Tavora's own live UI currently shows, at least
  in what this capture could see.)
- **The key quote, repeated at each step's footer**: **"we confirm the live price
  before you pay."** This is Tavora's own version of our assignment's §08 requirement
  (revalidate before booking, don't trust an old quote) — real-world precedent that
  this is exactly the right instinct, not an invented requirement.
- **No price-watch, alert, "notify me", or watchlist feature anywhere on this page
  either.** Only "My trips" (`/trips`) in the header nav, and WhatsApp support as the
  sole stated communication channel. This strongly suggests the feature we're building
  does not exist on Tavora's real product today — the assignment is testing whether we
  can design something genuinely new to them, not re-implement something they ship.
- **No day-by-day itinerary view, no room/tier picker, no traveller-count stepper**
  visible in this capture (trip summary states "2 people" as a fixed line with an
  "Edit trip" link back to `/plan`, not an inline stepper).
- **Cross-sell row** ("Complete your Manali trip"): Bus from ₹600/seat, Car from
  ₹17,700, Stays from ₹1,400/night, Things to do from ₹600/person — the only place a
  "stay" price appears at all in this capture, and it's a teaser "from" price, not tied
  to this specific trip's dates/room count.
- **No sold-out/limited-availability messaging observed** — only the generic loading
  copy mentioned above.
- **Layout top to bottom**: promo bar → header nav → trip summary block ("Your trip to
  Manali", "About Manali" link, "Add a second place" pills offering Kullu/Sissu,
  dates/duration/travellers line, "Edit trip") → 6-step progress indicator → step 1
  content (sidebar trip summary + "Pick a bus" + car listing cards) → loading state →
  cross-sell row → footer.
- Pages not fetched in this pass: `/plan` (already covered above), `/bus`, `/hotels`,
  and steps 2–6 of this same wizard (Stay/Extras/Return/Review weren't reachable from
  this single fetch of step 1).

---

## 2026-11-19 — Competitor landscape: how existing price-watch tools actually work

Researched the real products that already do something like what this assignment asks
for, to ground our design in how the industry actually approaches this (not guess at
it). Distinguishing **verified** (stated directly by the company/docs) from
**unverified** (third-party claim, marketing copy, or conflicting sources) throughout,
per the assignment's own instruction to do this.

**ixigo (India-specific — closest real-world analog to this assignment):**
- "Fare Intelligence" = Fare Prediction + Fare Alerts. *Verified*: prediction is
  domestic-flights-only, travel date up to 30 days out, uses historical price trends.
  *Verified*: alerts fire on price drops for tracked/preferred routes, delivered by
  email + push.
- **"Smart Lock"** (newer, AI-based) is the single most relevant real precedent: it
  monitors eligible fares continuously against a traveller's target budget, and once a
  fare within budget is found, **locks it** under a "Price Lock." If the fare rises
  after locking, ixigo covers the difference up to ₹4,000/traveller domestic (₹8,000
  international). *Unverified*: how the monitoring/locking is actually implemented
  internally — no technical detail published, this is product-facing description only.
  *Important caveat, verified*: the lock fee is non-refundable once charged, and the
  price guarantee covers fare only, not seat availability.
  [Source](https://www.mediainfoline.com/travel/ixigo-launches-smart-lock-an-agentic-ai-that-autonomously-monitors-and-locks-flight-fares)
  [Source](https://www.dqindia.com/ixigo-introduces-fare-intelligence-for-flight-bookings)
- **Why this matters for us**: Smart Lock is conceptually almost exactly our
  assignment's §06-§08 (monitor → budget-crossing alert → hold) in a shipped product.
  The "guarantee covers fare only, not availability" caveat is a good model for how we
  should phrase our own hold semantics honestly.

**Google Flights / Hopper (international reference, no deep technical detail public):**
- Both are explicitly trend/history-based predictors, not real-time guarantees.
  *Verified* (Google's own description, via a secondary source): price predictions
  rest on analysis of historical price trends for past flights; Price Forecast
  estimates 7-day direction with a stated confidence level.
  [Source](https://techcrunch.com/2016/10/17/google-flights-will-now-tell-you-when-fares-will-increase-help-you-find-cheaper-tickets/)
- Hopper's "Price Freeze" lets you lock a fare for up to 20 days for a small deposit
  ($10-20) — another real precedent for our hold/lock mechanic, though theirs is
  paid and longer-duration than our 2-minute simulated hold.
- *Unverified*: all specific accuracy numbers (Hopper's claimed "95% accuracy,"
  ixigo's "up to 40% savings") are marketing claims with no independent audit found.
  Treat every vendor accuracy claim in this space as unverified by default — this
  itself is a useful methodology note: don't let a vendor's claimed accuracy anchor our
  own freshness/confidence policy without saying it's unverified.
  [Source](https://thriftytraveler.com/guides/travel/use-hopper-cheap-airfare)

**Takeaway**: the "lock a price for a short window, cover/honor it if things move" vs.
"re-quote and get fresh consent after expiry" split (assignment §08) is exactly how the
two real products handling this best (ixigo Smart Lock, Hopper Price Freeze) already
work. We're not inventing an unusual mechanic — we're building a more rigorous,
engineering-correct version of a pattern that already exists commercially, with a much
shorter (2-minute) hold since this is a prototype, not a paid guarantee product.

## 2026-11-19 — Real data source landscape for flights/hotels/cabs (India)

Checked whether genuinely free/sandbox access exists per category, since §04 requires
real-or-sandbox retrieval *where accessible*, and an honestly-labeled simulated source
*where it is not*. Bottom line up front: **access is gated or ambiguous almost
everywhere we looked** — this is itself an important, evidenced finding, not just an
excuse to go synthetic.

**Flights:**
- **Amadeus Self-Service APIs** — *conflicting*: Amadeus's own docs describe a free
  Test tier (free monthly quota, 10 TPS, cached/limited data), but a 2026 third-party
  guide claims the free self-service portal was decommissioned July 17, 2026 and
  access now requires negotiated Enterprise terms. Could not resolve which is current
  without actually trying to register — that's a concrete next action, not a decision
  to make from search results alone. India domestic carrier coverage (IndiGo, Air
  India, SpiceJet, Akasa) in the test environment is vendor-claimed, not officially
  confirmed.
  [Source](https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/test-data/)
  [Source](https://geekflare.com/guides/flight-booking-api/)
- **Duffel** — the most concretely confirmed free sandbox found: "test mode" gives an
  unlimited test balance, a dedicated test airline ("Duffel Airways") with documented
  predictable origin-destination pairs for deterministic testing, and OAuth-style
  test tokens (`duffel_test_` prefix). **Important limitation, verified directly from
  Duffel's own help center**: test-mode prices are explicitly *not real, live prices*
  — seeing live prices requires full account activation. So even our "real" option
  here is really a realistic-contract sandbox, not live market data, for India routes.
  [Source](https://duffel.com/docs/api/overview/test-mode)
  [Source](https://help.duffel.com/hc/en-gb/articles/4410085835282-Are-the-flight-prices-in-test-mode-sandbox-real)
- **Kiwi.com Tequila** — reportedly closed to public self-serve signup since May 2024,
  now invitation/partnership-only per multiple sources, though one 2026 guide claims a
  limited free tier still exists. Conflicting enough that I would not rely on it
  without directly checking the partner portal.
- **SerpApi (Google Flights/Hotels via SERP scraping)** — free tier exists but its
  exact size is disputed across sources (100 vs 250 queries/month). This scrapes
  Google's own results rather than an airline/OTA API directly — real prices, but a
  different kind of "source" (search-engine-mediated) than a direct supplier API.

**Hotels:**
- **Booking.com Demand API** has a documented sandbox
  (`demandapi-sandbox.booking.com`), but *verified*: it requires registering as a
  Booking.com Managed Affiliate Partner and getting an API key + `X-Affiliate-Id`
  before the try-out console even works. Not a self-serve option for an independent
  7-day prototype.
  [Source](https://developers.booking.com/demand/docs/getting-started/sandbox)
- No independently-confirmed free, India-specific hotel pricing API was found.
  Third-party aggregators (MakCorps, Apify scrapers) exist but are either paid
  per-call or ToS-risky scrapers — the assignment explicitly rules out bypassing
  access controls, so scraping-based "APIs" are out regardless of price.

**Cabs / airport transfers:**
- **Ola** has a documented Ride Estimate API (pickup/drop coordinates in, fare range
  out), but access is *case-by-case, invite-only* via emailing their affiliates team —
  verified from Ola's own docs, not guaranteed for a 7-day window.
  [Source](https://developers.olacabs.com/docs/ride-estimate)
- **Uber**: no evidence found of current public India developer access for fare
  estimates. Unconfirmed either way — would need direct outreach to Uber's partner
  team to settle, not something resolvable by search.
- Airport pickup fee figures found (e.g. ₹150-218 range across operators at DEL/BLR)
  are a mix of third-party aggregator pages and vendor scraping samples — directionally
  useful for building a *realistic* synthetic fare model, but explicitly not something
  to cite as a live, current price.

**What this means for §04 (read together with the competitor research above)**:
the honest, defensible position is that a free/public real-time supplier integration
for all three categories, for India routes, inside a 7-day window, is not realistically
available — confirmed by actually checking each category rather than assumed. Duffel's
test mode is the strongest candidate for a genuinely real (if non-live-priced) flight
integration; hotels and cabs most likely need clearly-labeled synthetic sources with
realistic, cited contracts (fare ranges, occupancy rules, etc. grounded in the research
above, not invented from nothing). This is not a shortcut — it's exactly what §04 asks
for when a category is inaccessible, and we now have real evidence for *why* each
category is or isn't accessible, which is the thing the brief actually wants defended.

**Gaps still open, not yet researched**: hotel-specific and cab-specific competitor
products (we went deep on flight price-watching via ixigo/Google/Hopper, but haven't
looked at how any hotel-price-tracking or cab-fare-prediction product works
specifically — worth a pass if we want the same rigor across all three categories,
not just flights).

## 2026-11-19 — Competitor landscape, part 2: hotels and cabs

Closing the gap flagged at the end of the previous research pass — went deep on
flight price-watching (ixigo/Google/Hopper) but hadn't looked at hotel-price-tracking
or cab-fare-prediction products specifically. Same verified/unverified discipline as
before.

**Hotels:**
- Search turned up nothing on how Booking.com or Trivago run their own price-tracking
  or alerting internally — their methods aren't publicly documented (or weren't
  surfaced by this search). What *is* well documented is **Hopper**, which runs the
  closest hotel analog to its own flight product:
  - **Hopper hotel price prediction**: an algorithm combining historical price data,
    reviews, and other signals to forecast whether a hotel's rate will rise or fall.
    *Unverified*: Hopper's own claimed accuracy figures (up to "95% accuracy" cited by
    a third party) — company-sourced, no independent audit found, consistent with the
    pattern already seen on the flights side.
  - **Hopper "Price Freeze" for hotels** (launched June 2021) — the hotel equivalent of
    their flight freeze: pay a small deposit to lock a specific hotel's rate for up to
    60 days (terms vary by source — some cite 14 or 21 days instead, likely reflecting
    changes over time or partner-specific terms, e.g. the Capital One portal powered by
    Hopper). It is explicitly *not* a reservation with the hotel — it's framed as price
    insurance on a stay: if the rate rises during the freeze window, Hopper covers the
    difference up to a stated cap (~$100, with a maximum-difference threshold).
    [Source](https://media.hopper.com/news/hopper-announces-price-freeze-for-hotels-to-help-summer-travelers-lock-in)
    [Source](https://www.phocuswire.com/hopper-enables-commitment-free-hotel-price-lock)
  - **Kayak** forecasts 7-day price direction (rise/fall) from historical + real-time
    data — same trend-based pattern as Google Flights, just applied to hotel rates.
  - **Third-party trackers (e.g. PageCrawl)** work differently from all of the above:
    they monitor a specific booking-page URL and scrape the displayed room rate at
    intervals, alerting on an observed change rather than a forecast. This is actually
    the closest real-world analog to our own §06 monitoring-cycle mechanism (poll a
    priced page/endpoint on a schedule, compare to the last observation, alert on a
    meaningful change) — more structurally similar to what we're building than
    Hopper's prediction-model approach is.
  - No evidence found of a hotel-specific "lock + lose nothing + lose nothing" guarantee
    as generous as ixigo's flight Smart Lock — Hopper's hotel freeze is the closest,
    and it's a paid deposit product, not a free continuous-monitor-and-alert feature.
- **Takeaway**: hotels split into the same two mechanisms already seen on the flights
  side — trend-based prediction (Hopper, Kayak) vs. observed-price-change monitoring
  (scraping trackers) — and our own design (poll → compare → alert → hold) sits
  structurally closer to the second pattern than the first. This is a useful framing
  for the eventual Methodology Report: we're not building a price *predictor*, we're
  building a price *watcher*, and that's a real, named category of existing tool.

**Cabs:**
- **Uber's own published description of surge pricing** (the only cab-fare mechanism
  with real first-party documentation found): surge is automatic and algorithmic,
  driven by real-time, hyperlocal rider demand vs. driver availability; Uber states it
  also factors in forecasts about market conditions, and that drivers see a map of
  high-demand areas while riders can wait out a surge to avoid the higher price.
  *Verified* (Uber's own pages). *Unverified*: third-party claims that the algorithm
  also directly weighs weather, live events, and traffic as explicit inputs — plausible
  but not stated on Uber's own pages in what was found.
  [Source](https://www.uber.com/ca/en/drive/driver-app/how-surge-works/)
- **Ola**: no published algorithmic detail found at all — only generic third-party
  description ("continuously compares supply vs. demand"). This is consistent with the
  earlier finding that Ola's actual API access is invite-only/opaque — the whole
  product is less publicly documented than Uber's.
- **This is a fundamentally different mechanism from flights/hotels**: cab "pricing"
  here isn't a forecast or a tracked historical price at all — it's a real-time
  multiplier applied at request time based on current local supply/demand. There is no
  real-world "cab fare watcher/alert" product analog found anywhere (consistent with
  the earlier finding that no price-watch feature exists on Tavora's own site either).
  This matters for §04/§05: a cab-fare "source" for this project is honestly more like
  modeling a surge multiplier against a base fare than tracking a quoted price over
  time — a materially different synthetic-data problem than flights/hotels, not just a
  third instance of the same one.
- **India-specific regulatory ceiling, verified, directly useful for a realistic
  synthetic cab-fare model**: central government ride-hailing guidelines cap surge
  multipliers. The original 2020 rules capped surge at 1.5x the base fare (with a floor
  of 50% of base fare off-peak). A 2025 revision (Motor Vehicle Aggregator Guidelines
  2025) raised the peak-hour cap to **2x base fare**, keeping the 50%-of-base off-peak
  floor; states had a 3-month window to adopt it. No further change found for 2026.
  [Source](https://entrackr.com/news/govt-revises-ride-hailing-rules-2x-surge-cap-cancellation-fee-and-push-for-bike-taxis-9455586)
  [Source](https://www.techradar.com/news/india-fixes-surge-pricing-limits-for-uber-and-ola-drives)
- **Why this matters for us**: if cabs end up as a synthetic source (per the earlier
  finding that no accessible real API exists), these regulatory bounds (0.5x-2x of a
  base fare) give a real, citable, non-arbitrary range to anchor a synthetic surge
  model in — rather than inventing a multiplier range from nothing.

**Updated bottom line across all three categories**: flights and hotels both have real
industry patterns split between trend-prediction and observed-price-tracking (our
design sits in the tracking camp for both); cabs have no price-watching analog at all
because the underlying price isn't a trackable quote, it's a live multiplier — so a cab
"source" in this project will need to be framed and justified differently in the
Methodology Report than flights/hotels, not treated as a third identical case.

## 2026-11-19 — Repo + timeline + stack (see docs/DECISIONS.md for full reasoning)

- Private repo: `github.com/abhinavsingh-official/tavora-trip-watch`.
- Received Wed night 2026-11-18, demo Wed night 2026-11-25. Demo travel dates must be
  on/after 2026-12-25 (assignment's "30+ days after submission" rule).
- Backend: Python + FastAPI (settled). Frontend/DB/scheduler: still open.
- Confirmed with user: no AWS/cloud-provider infra for this project — the global
  CLAUDE.md infra-gate rules are scoped to company work, not this personal assignment.
