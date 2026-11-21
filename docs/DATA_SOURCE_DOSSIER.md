# Data-Source Dossier

*Condensed from `docs/research_summary.md` (11 research rounds) and
`docs/NOTES.md` (raw findings, 14 rounds). This document is the reference
answer for "where did the data come from and why" — full reasoning and every
rejected alternative is in those two files, not repeated here.*

## 1. Flights — Sabre Dev Studio (Bargain Finder Max v4)

| | |
|---|---|
| **Status** | Real, confirmed working |
| **Docs** | `developer.sabre.com` — Bargain Finder Max v4, OAuth2 token endpoint `POST /v2/auth/token` |
| **Access date confirmed** | 2026-11 (round 9 of research — real registration + real test calls, not docs review) |
| **Access model** | Free self-serve developer account; no business/KYC gate encountered |
| **Coverage** | Confirmed directly for this project's exact route (BOM⇄GOI); general India coverage vendor-documented |
| **Realism** | Schedule/carrier/timing data is real (real flight numbers, carriers, equipment); **fares come from a static test cell** — every result in a captured response carries the identical fixed INR/USD rate (96.5), the same tell as a sandbox/test-mode source elsewhere in the industry. Labeled "real schedule, test-cell fare" everywhere it's shown in the product, never claimed as live. |
| **Cost / rate limits** | Free tier; 7-day bearer token cached in memory rather than refetched per check |
| **Field mapping** | Sabre `OTA_AirLowFareSearchRS` → per-itinerary `TotalFare.Amount` → `PriceObservation.flight_outbound_price` / `flight_return_price` (outbound and return priced as two independent one-way searches); `Currency` field confirmed already INR, no conversion applied |
| **Fallback** | None needed — real sandbox reachable; `flight_status = "unavailable"` if the call fails or returns nothing for the route/date |
| **Rejected alternatives** | Amadeus Self-Service (free tier reportedly decommissioned, two corroborating secondary sources); Duffel (real signup attempt bounced on an apparent business-verification gate not described in its own docs); Kiwi.com Tequila (closed to public self-serve); direct IndiGo/Air India NDC (real APIs exist, partner-gated); Skyscanner (no self-serve path; unofficial scraper wrappers explicitly ruled out as access-control bypass) |

## 2. Hotels — Hotelbeds (HBX Group) Apitude API

| | |
|---|---|
| **Status** | Real, confirmed working |
| **Docs** | `developer.hotelbeds.com` — Hotel Content/Booking API, signature auth `SHA256(apikey + secret + timestamp)` |
| **Access date confirmed** | 2026-11 (round 10 reachability, round 11 Goa coverage, round 13 currency) |
| **Access model** | Free self-serve; four key pairs issued (Hotel/Activities/Transfers/Bundle) |
| **Coverage** | Confirmed via a real geolocation search returning 11 real, independently-verifiable Goa hotels (Kenilworth Beach Resort, The Zuri White Sands Goa Resort & Casino, Regenta Baywatch Resort Goa, others); destination code is the real `GOO` (not the guessed `GOA`), likewise confirmed real for Jaipur in round 14 |
| **Realism** | Real inventory and real hotel names; rate currency confirmed **EUR** via a real `CheckRates` call (Hotelbeds' own documented next step), converted to INR at one fixed, documented rate — explicitly labeled as approximate, not a live FX feed, everywhere it's shown |
| **Cost / rate limits** | Free tier — **50 requests/day**, confirmed scarce by exhausting it during research; documented burst limit of 8 requests/4 seconds, enforced in code with a thread-safe throttle (`app/rate_limit.py`); a 4-minute TTL cache (`app/ttl_cache.py`) absorbs repeat checks of the same query without changing real-price freshness |
| **Field mapping** | `CheckRates` response → cheapest rate line meeting `min_star_rating` and the full requested occupancy (`rooms`/`adults` in one line item, confirmed by inspecting the raw response directly) → `PriceObservation.hotel_total_price`; `net`/`currency` fields → the EUR→INR conversion |
| **Fallback** | None needed — real sandbox reachable; `hotel_status = "unavailable"` on failure or no matching inventory |
| **Operational gotchas (discovered directly, not documented)** | Broad/unfiltered content calls consume the daily quota fast — destination codes are fetched once and hardcoded, never re-queried per check; the `/locations/destinations` endpoint's `countryCode=` filter silently doesn't filter — only `codes=` (exact match) works |
| **Rejected alternatives** | Booking.com Demand API, TBO Holidays, Agoda, Expedia Rapid (all require a partnership/vetting process that can't complete in 7 days); RateHawk (real registration attempt confirmed gated to registered travel companies, and confirmed no INR pricing regardless); OYO (no price-search API exists at all — only an internal property-management API); scraper services (explicitly ruled out — the assignment forbids bypassing access controls) |

## 3. Cabs / airport transfers — simulated, with real anchors

| | |
|---|---|
| **Status** | Simulated — no reachable real fare source exists for this category in a 7-day window (six independent research rounds, including real attempts against Ola's and CabBazar's own documented APIs) |
| **Framing** | Modeled as a **fixed-quote airport-transfer product** (the Kiwitaxi/GetTransfer/Savaari/CabBazar shape — a pre-booked, point-to-point group transfer), not a ride-hail surge simulation — this matches the brief's own "destination airport transfer" wording and its "cab passenger/luggage capacity" requirement |
| **Real anchors used** | Official government per-km RTO/state taxi rate cards (e.g. Mumbai ₹21.90/km, Nagpur ₹28.80/km AC) as the primary anchor; the national Motor Vehicle Aggregator Guidelines' 0.5x–2x surge band as a sanity bound; the real ₹20–28/km tempo-traveller market rate (triangulated across 3 independent rental operators) for the 4+-adult vehicle class |
| **Vehicle-class logic** | Deterministic by adult count: sedan-class flat quote for ≤3 adults, tempo-traveller-class quote for 4+ adults, legs priced independently (outbound/return) |
| **Field mapping** | `pricing.py`'s synthetic formula → `PriceObservation.cab_outbound_price` / `cab_return_price`; always `cab_status = "complete"` (deterministic, never fails) — the one component that can't itself go `unavailable` |
| **Labeling** | Every screen that shows a cab price states it's simulated (`.simulated-banner` in the frontend) — never presented as if it came from a live supplier |
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
reproduced verbatim, in `docs/NOTES.md`.

## 6. Freshness and fallback summary

| Category | Freshness | Fallback on failure |
|---|---|---|
| Flights | Real-time call, schedule-real / fare-test-cell, 4-min TTL cache per query | `flight_status = "unavailable"`, whole package marked incomplete, no alert possible |
| Hotels | Real-time call, 4-min TTL cache per query, rate-limited to respect the 50/day quota | `hotel_status = "unavailable"`, whole package marked incomplete |
| Cabs | Deterministic synthetic formula, always available | N/A — this component cannot itself fail |

Full per-round research detail, every rejected source's exact reasoning, and
the four real registration/test attempts that settled open questions (Duffel,
Sabre, Hotelbeds, RateHawk) are in `docs/research_summary.md` §6–8.
