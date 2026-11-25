# Data Sources

*Sources evaluated and selected, per category, across 11 research rounds of real registrations and
test calls - not just documentation review.*

## 1. Flights - Sabre Dev Studio (Bargain Finder Max v4)

Real sandbox; synthetic directory on the live path.

| | |
|---|---|
| **Status** | Real, confirmed working (`app/sabre_client.py`). Kept as proof of real access, but the live app no longer prices from it on the normal request path (see 1a). |
| **Docs** | `developer.sabre.com` - BFM v4, OAuth2 `POST /v2/auth/token` |
| **Access confirmed** | 2026-11, via real registration + test calls |
| **Access model** | Free self-serve; no KYC gate |
| **Coverage** | Confirmed for BOM⇄GOI; India coverage vendor-documented |
| **Realism** | Schedule/carrier/timing real; fares are a frozen test-cell rate (identical INR/USD rate, 96.5, on every call) - a frozen fare can't demo monitoring, hence moved off the live path |
| **Cost / limits** | Free tier; 7-day bearer token cached in memory |
| **Field mapping** | `TotalFare.Amount` → `flight_outbound_price`/`flight_return_price`; `Currency` already INR |
| **Fallback role** | Live-call fallback for any route/date not in the synthetic directory; `flight_status = "unavailable"` if that also fails |
| **Rejected** | Amadeus (free tier decommissioned); Duffel (signup blocked, business-verification gate); Kiwi Tequila (no public self-serve); IndiGo/Air India NDC (partner-gated); Skyscanner (no self-serve; scraping ruled out) |

### 1a. Every flight source evaluated, not just the ones picked

| Source | Access model | Why rejected |
|---|---|---|
| Amadeus Self-Service | Free test tier, two corroborating reports say decommissioned (one dated 2026-07-17) | Access status unresolved, likely gone |
| Kiwi.com Tequila | Reportedly closed to public self-serve since 2024-05 | No reliable self-serve path |
| Travelpayouts real-time Flight Search API | Real, but gated to projects with 50,000+ monthly active users | Structurally inaccessible at this project's scale |
| Skyscanner official partner API | Commercial partnership only (~100k MAU) | No self-serve path exists |
| Skyscanner via RapidAPI/Apify scraper wrappers | "Free tier" via unofficial scrapers of a protected search page | Ruled out outright - scraping a protected product is exactly what the brief forbids |
| IndiGo / Air India NDC | Real, documented NDC APIs exist for both | Explicitly partner-gated, not self-serve |
| SerpApi (Google Flights scrape) | Free tier, real scraped results | Quota too uncertain to be primary; search-engine-mediated, not a direct supplier |
| Travelpayouts Aviasales Data API | Free, self-serve, real but historical/trend data | Not a live point-in-time quote - kept as a supplementary baseline signal instead (§4) |
| Yatra NDC / TBO / Tripjack (flights) | Corporate booking product or B2B vetting gate | Same gate shape as the hotel B2B sources below |

### 1b. Flights as actually served - synthetic directory

- `SyntheticFlightOption`, generated once by `generate_synthetic_data.py`, deterministic per route+date (replayable per Sec. 11): 10 options/leg × 6 real legs = 60 rows.
- Real IATA codes and real India carriers (IndiGo/Air India/Vistara/SpiceJet/AirAsia India/Akasa), prices synthetic.
- `base_price_inr`/`current_price_inr` are per-adult, anchored to the one real Sabre capture (BOM→GOI ≈₹3,750/adult); other routes estimated at the same order of magnitude.
- `current_price_inr` drifts via `price_mutation.py` (§7), clamped ±30% of base.
- Uncached route/date/stops → real Sabre fallback, never a fabricated price.

## 2. Hotels - Hotelbeds (HBX Group) Apitude API

| | |
|---|---|
| **Status** | Real, confirmed working. Live product reads a pre-fetched cache (§2b); real live call is the fallback. |
| **Docs** | `developer.hotelbeds.com` - signature auth `SHA256(apikey+secret+timestamp)` |
| **Access confirmed** | 2026-11 (reachability, Goa coverage, currency - rounds 10/11/13) |
| **Access model** | Free self-serve; two sandbox accounts (see §2b) |
| **Coverage** | Real geolocation search, real hotels (Kenilworth Beach Resort, The Zuri White Sands, Regenta Baywatch); real `GOO` destination code |
| **Realism** | Real inventory/names; rate currency EUR (confirmed via `CheckRates`), converted to INR at a live daily rate (`app/exchange_rate.py`, fixed-rate fallback only if that lookup fails) |
| **Cost / limits** | Free tier, 50 req/day (confirmed scarce by exhausting it); 8 req/4s burst throttle (`rate_limit.py`); 4-min TTL cache (`ttl_cache.py`) |
| **Field mapping** | Cheapest eligible rate meeting `min_star_rating` → `CachedHotelOption.price_eur` → `hotel_total_price` |
| **Fallback** | Uncached (destination, dates, occupancy) → real live call; `hotel_status = "unavailable"` if that fails too |
| **Gotchas found live** | Destination codes hardcoded (quota-expensive otherwise); `countryCode=` filter silently no-ops, only `codes=` works; **`occupancies` needs one entry per room** - a combined entry starved multi-room search (User B: 5 hotels found vs. 47 once split), confirmed by live A/B test. Total for N rooms = per-room rate × N. |
| **Rejected** | Booking.com Demand, TBO, Agoda, Expedia Rapid (partnership-gated); RateHawk (B2B-gated, no INR); OYO (no price-search API); scrapers (ruled out by brief) |

### 2a. Every hotel source evaluated, not just the ones picked

| Source | Access model | Why rejected |
|---|---|---|
| Booking.com Demand API | Must become an approved Managed Affiliate Partner before the sandbox unlocks | Approval won't complete in a 7-day window |
| TBO Holidays | B2B only - vetted travel agency, security deposit or credit line | Same timeline problem as Booking.com |
| RateHawk (ETG API v3) | Real registration attempt confirmed gated to registered travel companies | Also confirmed no INR pricing even where access exists - two independent disqualifiers |
| Agoda | Partnership-gated, case-by-case | No self-serve path; unofficial scrapers ruled out on the same grounds as other scrapers |
| Expedia Rapid API (+ Hotels.com inventory) | Sandbox access must be requested from an Expedia account manager | Confirmed gated, no self-serve path despite a reseller's 7-day trial offer |
| OYO | No price-search API exists at all - the one "Open API" found is an internal property-management API for onboarded hotel owners | Wrong product entirely, not merely inaccessible |
| MakCorps / Apify-style scrapers | Paid per-call, or ToS-risky scraping | Explicitly disallowed by the brief regardless of cost |
| Yatra / EaseMyTrip / Cleartrip (hotels) | Programmatic access only via third-party B2B integration vendors | Same B2B-gate shape as Booking.com/TBO/Agoda |

### 2b. Hotels as actually served - pre-fetched cache

- Hotelbeds' 50/day quota can't cover hundreds of monitoring cycles, so `fetch_hotel_directory.py` pre-fetches real inventory once per demo search key, on a second sandbox account reserved for this (never on the live path).
- Real result: 48 hotels (User A), 47 (User B), 20 (User C) - real names/ratings/rates.
- `hotels.py` reads this table first; `price_eur` drifts via §7, clamped ±30% of the real fetched rate.
- Edited-away search key → real live call on the primary account.

## 3. Cabs / airport transfers - simulated, with real anchors

| | |
|---|---|
| **Status** | Simulated - no reachable real fare source in 7 days (6 research rounds incl. real Ola/CabBazar attempts) |
| **Framing** | Fixed-quote airport transfer (Kiwitaxi/Savaari/CabBazar shape), matching the brief's own wording - not ride-hail surge |
| **Real anchors** | Govt RTO rate cards (Mumbai ₹21.90/km, Nagpur ₹28.80/km AC); national surge band 0.5x–2x as sanity bound; ₹20–28/km tempo-traveller rate (3 operators) |
| **Vehicle classes** | `SyntheticCabOption`: 2 sedans, 1 SUV, 1 tempo traveller, each with vendor/capacity/luggage. Price = `distance_km × per_km_rate_inr` (~30km assumed transfer, ₹14–24/km by class), shown alongside the price. Cheapest option that fits party + baggage wins; too-large party → `unavailable` (never triggered by the 3 demo users). |
| **Field mapping** | → `cab_outbound_price`/`cab_return_price`; `unavailable` now reachable |
| **Price movement** | Drifts via §7, clamped ±30% of each class's anchored base |
| **Labeling** | Always shown as simulated |
| **Rejected** | Ola Outstation (best real contract found, invite-only); CabBazar (real, vetted-business-gated); Uber (gated, and ToS forbids price-comparison use) |

### 3a. Every cab/transfer source evaluated, not just the ones picked

Six research rounds, including a re-framing: a ride-hail fare isn't a quote you can hold since it's
computed live at request time, but a **fixed-quote airport-transfer** (Kiwitaxi/Savaari/CabBazar
shape) is a real, named commercial category that matches the brief's own "destination airport
transfer" wording - this changed how the cab leg was modeled, not just which API was tried.

| Source | Access model | Why rejected |
|---|---|---|
| Uber price-estimate API | Gated behind Uber's approval | Confirmed ToS conflict - Uber's API Terms of Use explicitly prohibit price-comparison use cases, directly relevant to this project's purpose |
| Ola Ride Estimate API | Invite-only, case-by-case via email to the affiliates team | No guaranteed turnaround |
| Ola Outstation API | The single strongest documented cab-fare contract found - real fare-breakup fields, a real booking/cancellation endpoint | Same invite-only, case-by-case gate as the Ride Estimate API |
| CabBazar cab-booking API | Real, documented API covering outstation transfers and airport taxi specifically | Requires contacting CabBazar with a business profile and expected sales volume |
| Savaari.com, Carzonrent India | Real, established Indian outstation/airport-transfer operators; Savaari's fleet confirmed to include tempo travellers | No public developer API at all - consumer booking only |
| Kiwitaxi | Fixed, pre-quoted transfer pricing | Only reachable via a third-party reseller (PHPTRAVELS), not a direct signup |
| GetTransfer | Fixed/quoted pricing via a documented `route_info` endpoint | Only documented by a third party (Travelpayouts), not GetTransfer's own developer docs - needs direct verification |
| 12Go Asia | Real partner API for scheduled multimodal transport (bus/train/ferry) | Wrong category - a scheduled public-transport marketplace, not a private point-to-point group transfer |
| Rome2Rio | Historically free/self-serve for routing | Not a fare source at all - its own docs say it doesn't provide live transit prices or airfares |
| ixigo Cabs | Consumer aggregator over Ola/Uber/Easycabs | No API, aggregator only |

Real anchors used instead: official government per-km RTO/state taxi rate cards (Mumbai ₹21.90/km,
Nagpur ₹28.80/km AC, Karnataka ~₹18.66/km), the national Motor Vehicle Aggregator Guidelines' 0.5x-2x
surge band as a sanity bound, Google Routes API for real driving distance, and the real ₹20-28/km
tempo-traveller market rate (triangulated across 3 independent rental operators) for larger vehicle
classes.

## 4. Supporting, non-pricing real data

| Source | Used for | Status |
|---|---|---|
| Google Routes API | Real driving distance for the cab formula | Real, free, 70k events/mo quota |
| Travelpayouts Aviasales | Baseline fare range to sanity-check Sabre | Real, free, trend data only |

## 5. Real request/response payload (Hotelbeds Availability search)

The actual request this app sends for User A's trip (Mumbai → Goa, 2 adults, 1 room,
2026-12-26 → 2026-12-29) - built by `app/hotelbeds_client.py::search_hotels`, not illustrative:

```json
POST https://api.test.hotelbeds.com/hotel-api/1.0/hotels
{
  "stay": { "checkIn": "2026-12-26", "checkOut": "2026-12-29" },
  "occupancies": [
    { "rooms": 1, "adults": 2, "children": 0 }
  ],
  "geolocation": {
    "latitude": 15.2993,
    "longitude": 74.124,
    "radius": 30,
    "unit": "km"
  }
}
```
(Signed via `Api-key` + `X-Signature: SHA256(apikey+secret+timestamp)` headers, not a request body
field - see `_sign()`/`_headers()` in the same file.)

A real response row this search actually returned and cached (`cached_hotel_options`, hotel code
957502, confirmed live against the sandbox, not fabricated):

```json
{
  "hotels": {
    "hotels": [
      {
        "code": 957502,
        "name": "Calangute Villae By Urban Getaway",
        "categoryName": "1 STAR",
        "rooms": [
          {
            "name": "Deluxe",
            "rates": [
              { "rateKey": "<opaque, per-search, expires in minutes>", "net": "63.24", "rooms": 1, "adults": 2, "paymentType": "AT_WEB" }
            ]
          }
        ]
      }
    ]
  }
}
```
`rateKey` is the one field genuinely impossible to reproduce verbatim - Hotelbeds mints a fresh,
encrypted, time-limited key per search, specifically so it can't be cached or replayed as a static
value. Every other field above is this project's own real cached row.

## 6. Freshness and fallback summary

| Category | Freshness | Fallback on failure |
|---|---|---|
| Flights | Synthetic directory, drifts via §7; real Sabre call for uncached route/date | `unavailable`, package incomplete, no alert |
| Hotels | Real data, pre-fetched once, drifts via §7; real live call for uncached key | `unavailable` |
| Cabs | Synthetic directory, drifts via §7 | `unavailable` if nothing fits party/baggage |

## 7. Price-mutation layer (`app/price_mutation.py`)

Sabre's fares are frozen, the hotel pre-fetch is a snapshot, and the cab
directory doesn't move on its own - without drift, "check and alert on a
drop" would have nothing to demonstrate.

- `mutate_all_prices()` nudges each market (one route, one hotel search key, the shared cab list)
  by a small random step (±4%), reflecting off a ±30% band around its own base price rather than
  flatlining at the edge, so it keeps moving instead of visibly freezing after enough same-direction
  steps.
- Each market independently has a chance to sit still for a given cycle instead of moving (not
  every real price changes every 5 minutes either) - a per-group decision, not an app-wide on/off
  switch, so different routes/hotels genuinely move independently rather than all jumping in
  lockstep every few cycles.
- Runs every real 5-min cycle (`scheduler.py::run_one_cycle`), not gated behind any counter that
  could reset across a process restart; `POST /api/lab/mutate-prices` triggers it on demand for
  demo pacing, separately from `/trigger-cycle` (mutate + check + alert in one step).
- Always a synthetic layer on a real/anchored base price - never presented as a live feed.

Four real registration attempts settled the open questions above: Duffel (rejected, registration
blocked), Sabre (confirmed working), Hotelbeds (confirmed working), RateHawk (rejected, gated to
registered travel companies).

## 8. Frontend imagery (`frontend/public/images/`)

Four decorative photos (Pexels, free-to-use) for visual polish only - not
photos of any real hotel/flight/vehicle, not tied to the synthetic/real
candidates they sit next to. Disclosed per Sec. 04's labelling requirement.
