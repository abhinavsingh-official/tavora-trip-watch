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

### 1a. Flights as actually served - synthetic directory

- `SyntheticFlightOption`, generated once by `generate_synthetic_data.py`, deterministic per route+date (replayable per Sec. 11): 10 options/leg × 6 real legs = 60 rows.
- Real IATA codes and real India carriers (IndiGo/Air India/Vistara/SpiceJet/AirAsia India/Akasa), prices synthetic.
- `base_price_inr`/`current_price_inr` are per-adult, anchored to the one real Sabre capture (BOM→GOI ≈₹3,750/adult); other routes estimated at the same order of magnitude.
- `current_price_inr` drifts via `price_mutation.py` (§7), clamped ±30% of base.
- Uncached route/date/stops → real Sabre fallback, never a fabricated price.

## 2. Hotels - Hotelbeds (HBX Group) Apitude API

| | |
|---|---|
| **Status** | Real, confirmed working. Live product reads a pre-fetched cache (§2a); real live call is the fallback. |
| **Docs** | `developer.hotelbeds.com` - signature auth `SHA256(apikey+secret+timestamp)` |
| **Access confirmed** | 2026-11 (reachability, Goa coverage, currency - rounds 10/11/13) |
| **Access model** | Free self-serve; two sandbox accounts (see §2a) |
| **Coverage** | Real geolocation search, real hotels (Kenilworth Beach Resort, The Zuri White Sands, Regenta Baywatch); real `GOO` destination code |
| **Realism** | Real inventory/names; rate currency EUR (confirmed via `CheckRates`), converted to INR at one fixed documented rate |
| **Cost / limits** | Free tier, 50 req/day (confirmed scarce by exhausting it); 8 req/4s burst throttle (`rate_limit.py`); 4-min TTL cache (`ttl_cache.py`) |
| **Field mapping** | Cheapest eligible rate meeting `min_star_rating` → `CachedHotelOption.price_eur` → `hotel_total_price` |
| **Fallback** | Uncached (destination, dates, occupancy) → real live call; `hotel_status = "unavailable"` if that fails too |
| **Gotchas found live** | Destination codes hardcoded (quota-expensive otherwise); `countryCode=` filter silently no-ops, only `codes=` works; **`occupancies` needs one entry per room** - a combined entry starved multi-room search (User B: 5 hotels found vs. 47 once split), confirmed by live A/B test. Total for N rooms = per-room rate × N. |
| **Rejected** | Booking.com Demand, TBO, Agoda, Expedia Rapid (partnership-gated); RateHawk (B2B-gated, no INR); OYO (no price-search API); scrapers (ruled out by brief) |

### 2a. Hotels as actually served - pre-fetched cache

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

## 4. Supporting, non-pricing real data

| Source | Used for | Status |
|---|---|---|
| Google Routes API | Real driving distance for the cab formula | Real, free, 70k events/mo quota |
| Travelpayouts Aviasales | Baseline fare range to sanity-check Sabre | Real, free, trend data only |

## 5. Sanitized sample payload (Hotelbeds `CheckRates`, abridged)

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
Illustrative, not a live response - the real captures behind this (with real hotel names) were taken
during research and aren't reproduced verbatim here.

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

- `mutate_all_prices()` nudges every price by a small random step (±4%/call), clamped to ±30% of its own base - holds even after 200 calls.
- Runs automatically once per real 5-min cycle (`scheduler.py::run_one_cycle`); `POST /api/lab/mutate-prices` triggers it on demand for demo pacing, separately from `/trigger-cycle` (mutate + check + alert in one step).
- Always a synthetic layer on a real/anchored base price - never presented as a live feed.

Four real registration attempts settled the open questions above: Duffel (rejected, registration
blocked), Sabre (confirmed working), Hotelbeds (confirmed working), RateHawk (rejected, gated to
registered travel companies).

## 8. Frontend imagery (`frontend/public/images/`)

Four decorative photos (Pexels, free-to-use) for visual polish only - not
photos of any real hotel/flight/vehicle, not tied to the synthetic/real
candidates they sit next to. Disclosed per Sec. 04's labelling requirement.
