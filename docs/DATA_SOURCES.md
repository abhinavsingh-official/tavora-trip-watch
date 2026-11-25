# Data Sources

*Condensed from `docs/internal/research-summary.md` (11 research rounds) and
`docs/internal/research-notes-raw.md` (raw findings, 14 rounds). This document is the reference
answer for "where did the data come from and why" — full reasoning and every
rejected alternative is in those two files, not repeated here.*

## 1. Flights — Sabre Dev Studio (Bargain Finder Max v4), real; synthetic directory on the live path

| | |
|---|---|
| **Status** | Real, confirmed working — kept in the codebase (`app/sabre_client.py`, `app/sources/flights.py`'s live-call fallback) as proof of real, working access, documented here in full. **The live product's actual flight data no longer comes from this on the normal request path** (see below). |
| **Docs** | `developer.sabre.com` — Bargain Finder Max v4, OAuth2 token endpoint `POST /v2/auth/token` |
| **Access date confirmed** | 2026-11 (round 9 of research — real registration + real test calls, not docs review) |
| **Access model** | Free self-serve developer account; no business/KYC gate encountered |
| **Coverage** | Confirmed directly for this project's exact route (BOM⇄GOI); general India coverage vendor-documented |
| **Realism** | Schedule/carrier/timing data is real (real flight numbers, carriers, equipment); **fares come from a static test cell** — every result in a captured response carries the identical fixed INR/USD rate (96.5), the same tell as a sandbox/test-mode source elsewhere in the industry. This is exactly why it was moved off the live path: a frozen fare can never demonstrate monitoring/alerting (Sec. 06/07), regardless of how real the underlying call is. |
| **Cost / rate limits** | Free tier; 7-day bearer token cached in memory rather than refetched per check |
| **Field mapping** | Sabre `OTA_AirLowFareSearchRS` → per-itinerary `TotalFare.Amount` → `PriceObservation.flight_outbound_price` / `flight_return_price` (outbound and return priced as two independent one-way searches); `Currency` field confirmed already INR, no conversion applied |
| **Fallback role today** | Still the real live-call fallback for any route/date/stops combination the synthetic directory below doesn't cover (e.g. a request edited away from the three demo seeds) — `flight_status = "unavailable"` if that call also fails or returns nothing |
| **Rejected alternatives** | Amadeus Self-Service (free tier reportedly decommissioned, two corroborating secondary sources); Duffel (real signup attempt bounced on an apparent business-verification gate not described in its own docs); Kiwi.com Tequila (closed to public self-serve); direct IndiGo/Air India NDC (real APIs exist, partner-gated); Skyscanner (no self-serve path; unofficial scraper wrappers explicitly ruled out as access-control bypass) |

### 1a. Flights as actually served — synthetic directory (`SyntheticFlightOption`, labeled synthetic everywhere)

Generated once by `backend/scripts/generate_synthetic_data.py`, deterministically seeded per
route+date (same input → same directory, replayable per Sec. 11), 10 options per leg across the three
demo users' six real legs (60 rows total). Uses the *same real route/airport shape* Sabre confirmed
(real IATA codes, real India domestic carriers — IndiGo/Air India/Vistara/SpiceJet/AirAsia
India/Akasa — operating these routes in reality) so the directory looks like a real result set, while
every price is clearly synthetic. `base_price_inr`/`current_price_inr` are **per adult**, anchored to
the one real Sabre observation this project captured (BOM→GOI, 2 adults, ≈₹7,492 total → ≈₹3,750/adult)
and estimated for the other two routes at the same per-adult order of magnitude. `current_price_inr` is
what pricing actually reads; it's nudged over real time by `app/price_mutation.py` (§7 below), clamped
to ±30% of `base_price_inr` so it drifts without running away. A route/date/max-stops combination not
in this directory falls back to the real Sabre call above — never a fabricated price if that also
fails.

## 2. Hotels — Hotelbeds (HBX Group) Apitude API

| | |
|---|---|
| **Status** | Real, confirmed working. The live product reads a real, pre-fetched cache (`CachedHotelOption`) rather than calling Hotelbeds on every check — see §2a — with a genuine live call kept as the fallback for anything not cached. |
| **Docs** | `developer.hotelbeds.com` — Hotel Content/Booking API, signature auth `SHA256(apikey + secret + timestamp)` |
| **Access date confirmed** | 2026-11 (round 10 reachability, round 11 Goa coverage, round 13 currency) |
| **Access model** | Free self-serve; four key pairs issued per account (Hotel/Activities/Transfers/Bundle); **two separate sandbox accounts** exist — see §2a for why |
| **Coverage** | Confirmed via a real geolocation search returning real, independently-verifiable hotels by name (e.g. Kenilworth Beach Resort, The Zuri White Sands Goa Resort & Casino, Regenta Baywatch Resort Goa); destination code is the real `GOO` (not the guessed `GOA`), likewise confirmed real for Jaipur in round 14 |
| **Realism** | Real inventory and real hotel names; rate currency confirmed **EUR** via a real `CheckRates`-equivalent response, converted to INR at one fixed, documented rate — explicitly labeled as approximate, not a live FX feed, everywhere it's shown |
| **Cost / rate limits** | Free tier — **50 requests/day per account**, confirmed scarce by exhausting it during research; documented burst limit of 8 requests/4 seconds, enforced in code with a thread-safe throttle (`app/rate_limit.py`); a 4-minute TTL cache (`app/ttl_cache.py`) absorbs repeat checks of the same query without changing real-price freshness |
| **Field mapping** | `hotel-api/1.0/hotels` response → each hotel's cheapest eligible rate line meeting `min_star_rating`, for the full requested occupancy → `CachedHotelOption.price_eur` at seed time, `PriceObservation.hotel_total_price` at check time; `net`/`currency` fields → the EUR→INR conversion |
| **Fallback** | A request whose exact (destination, dates, occupancy) isn't cached falls back to a real live call on the primary account; `hotel_status = "unavailable"` if that also fails or returns no matching inventory |
| **Operational gotchas (discovered directly, not documented)** | Broad/unfiltered content calls consume the daily quota fast — destination codes are fetched once and hardcoded, never re-queried per check; the `/locations/destinations` endpoint's `countryCode=` filter silently doesn't filter — only `codes=` (exact match) works. **New this session**: the `occupancies` field must be one entry *per room*, each with its own adults count — not one combined entry with `rooms` as a multiplier. The combined shape silently starved multi-room searches: User B's exact 2-room/4-adult search returned only 5 priced hotels with the combined shape, and 47 once split into two `{"rooms":1,"adults":2}` entries, confirmed via a real side-by-side live test. Each rate line is genuinely per-room (confirmed via its own embedded `"rooms":1` field), so the total for N rooms is that per-room rate × N, computed once at seed time. |
| **Rejected alternatives** | Booking.com Demand API, TBO Holidays, Agoda, Expedia Rapid (all require a partnership/vetting process that can't complete in 7 days); RateHawk (real registration attempt confirmed gated to registered travel companies, and confirmed no INR pricing regardless); OYO (no price-search API exists at all — only an internal property-management API); scraper services (explicitly ruled out — the assignment forbids bypassing access controls) |

### 2a. Hotels as actually served — a real, pre-fetched cache (`CachedHotelOption`)

Hotelbeds' 50/day quota can't sustain calling it on every one of hundreds of monitoring cycles, so
`backend/scripts/fetch_hotel_directory.py` pre-fetches real inventory **once** for each of the three
demo users' exact (destination, dates, occupancy) search key, using a **second, separately-issued
sandbox account** reserved for exactly this ("fallback" in `.env`, never used on the live request path
— not a routine quota-doubling, a one-time bulk seed). Real result: 48 real hotels for User A, 47 for
User B, 20 for User C (115 total) — all real names, real star ratings, real room descriptions, real
rates. `hotels.py` reads this table first; `price_eur` is nudged over time by `app/price_mutation.py`
(§7), clamped to the real fetched rate (`base_price_eur`) ±30%, so repeated checks show real inventory
at a realistically drifting price rather than one frozen snapshot. A request edited away from the three
seeded search keys falls back to a real live call on the primary account.

## 3. Cabs / airport transfers — simulated, with real anchors

| | |
|---|---|
| **Status** | Simulated — no reachable real fare source exists for this category in a 7-day window (six independent research rounds, including real attempts against Ola's and CabBazar's own documented APIs) |
| **Framing** | Modeled as a **fixed-quote airport-transfer product** (the Kiwitaxi/GetTransfer/Savaari/CabBazar shape — a pre-booked, point-to-point group transfer), not a ride-hail surge simulation — this matches the brief's own "destination airport transfer" wording and its "cab passenger/luggage capacity" requirement |
| **Real anchors used** | Official government per-km RTO/state taxi rate cards (e.g. Mumbai ₹21.90/km, Nagpur ₹28.80/km AC) as the primary anchor; the national Motor Vehicle Aggregator Guidelines' 0.5x–2x surge band as a sanity bound; the real ₹20–28/km tempo-traveller market rate (triangulated across 3 independent rental operators) for the larger vehicle classes |
| **Vehicle-class logic (now a real directory, `SyntheticCabOption`)** | Previously one flat formula picked by an adult-count threshold; now 4 labeled vehicle classes (2 sedans, 1 SUV, 1 tempo traveller — vendor name, passenger capacity, luggage capacity), generated by `scripts/generate_synthetic_data.py` from the same real anchors above. Each class's price is `distance_km × per_km_rate_inr` (an assumed ~30km representative airport-to-hotel transfer times a real per-km market rate for that class — ₹14–24/km across the 4 classes), not a flat guessed number, and both figures are shown alongside the price in the UI. `sources/cabs.py` picks the **cheapest option whose passenger capacity actually fits the party**, and (new) whose luggage capacity actually fits the request's checked-baggage need — the first real enforcement of Sec. 05's cab capacity requirement; a party too large for every class now reports `unavailable` rather than being silently fit into something too small. None of the three real demo users are large enough to ever trigger that. |
| **Field mapping** | `sources/cabs.py` → `PriceObservation.cab_outbound_price` / `cab_return_price`; `cab_status = "unavailable"` is now reachable (see above) — no longer unconditionally `"complete"` |
| **Price movement** | `current_price_per_leg_inr` is nudged over real time by `app/price_mutation.py` (§7), clamped to ±30% of each vehicle class's own anchored base price |
| **Labeling** | Every screen that shows a cab price states it's simulated — never presented as if it came from a live supplier |
| **Rejected/gated real APIs found** | Ola Outstation API (the single most concrete documented cab-fare contract found — real fields, real booking/cancellation endpoints — but access is invite-only, case-by-case, no guaranteed turnaround); CabBazar cab-booking API (real, documented, covers airport-taxi specifically — gated to vetted business accounts); Uber (price-estimate endpoint gated, and its API Terms of Use explicitly prohibit price-comparison use cases — a contractual conflict with this project's purpose, not just an access gap) |

## 4. Supporting, non-pricing real data

| Source | Used for | Status |
|---|---|---|
| Google Routes API ("Compute Route Matrix") | Real driving distance to ground the synthetic cab formula | Real, free self-serve, confirmed India-specific 70,000 free events/month quota |
| Travelpayouts Aviasales Data API | Real trend/baseline fare range to sanity-check Sabre's test-cell fares against | Real, free self-serve, trend data not live point-in-time quotes |

## 5. Sanitized sample raw payload (Hotelbeds `CheckRates`, abridged)

```json
{
  "hotel": {
    "code": 123456,
    "name": "Example Beach Resort Goa",
    "currency": "EUR",
    "rooms": [
      {
        "rates": [
          { "rateKey": "...", "net": "148.50", "rooms": 2, "adults": 4, "paymentType": "AT_WEB" }
        ]
      }
    ]
  }
}
```
Hotel name and `rateKey` above are illustrative, not a live response — the
real captured responses (with real hotel names) are referenced, not
reproduced verbatim, in `docs/internal/research-notes-raw.md`.

## 6. Freshness and fallback summary

| Category | Freshness | Fallback on failure |
|---|---|---|
| Flights | Synthetic directory, generated once, drifting slowly via §7's mutation layer; real Sabre call as fallback for an uncached route/date | `flight_status = "unavailable"` if the fallback call also fails, whole package marked incomplete, no alert possible |
| Hotels | Real data, pre-fetched once per demo search key, drifting slowly via §7; real live call as fallback for an uncached search key | `hotel_status = "unavailable"` if the fallback call also fails or finds nothing |
| Cabs | Synthetic vehicle-class directory, drifting slowly via §7 | `cab_status = "unavailable"` if no vehicle class fits the party/baggage — newly reachable, previously impossible |

## 7. Price-mutation layer (`app/price_mutation.py`) — why monitoring has anything to actually watch

Sabre's sandbox fares are frozen (a documented property of its test cell, §1), a one-time hotel
pre-fetch is by definition a snapshot, and a synthetic cab directory doesn't move on its own either.
Without something making these numbers drift, "keep checking and alert on a drop" (Sec. 06/07) would
have nothing real to demonstrate in default usage — every repeated check would return the exact same
total forever.

`mutate_all_prices()` nudges every synthetic flight/cab price and the cached hotel price by a small
random step (±4% per call), **clamped to within ±30% of that row's own real/generated base value** —
verified to hold even after 200 repeated calls — so a long demo session drifts believably around its
real-anchored baseline rather than wandering off to something absurd. It runs automatically once per
real 5-minute monitoring cycle (`scheduler.py::run_one_cycle`), and can be triggered on demand via
`POST /api/lab/mutate-prices` for live-demo pacing, separately from `POST /api/lab/trigger-cycle`
(which mutates *and* immediately checks/alerts in one step). Always clearly a synthetic movement layered
on top of a real or realistically-anchored base price — never presented as a live market feed.

Full per-round research detail, every rejected source's exact reasoning, and
the four real registration/test attempts that settled open questions (Duffel,
Sabre, Hotelbeds, RateHawk) are in `docs/internal/research-summary.md` §6–8.

## 8. Frontend imagery (`frontend/public/images/`)

Four decorative photos (destination hero, generic hotel/flight/cab accents on the "Your Bookings"
cards) sourced from Pexels (images.pexels.com), a free-to-use stock photo library. These are
**stock imagery for visual polish only** — not photos of any real hotel,
flight, or vehicle referenced elsewhere in the app, and not tied to the actual synthetic/real
candidates they sit next to. Disclosed here per Sec. 04's labelling requirement.
