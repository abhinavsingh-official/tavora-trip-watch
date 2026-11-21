# Version 1 — module breakdown

*Written before implementation, as the exact build spec for V1. Every file listed
here is what gets created next, in this order, nothing more. Cross-reference against
`docs/versions/V1.md` (what V1 does/doesn't do) and `docs/DECISIONS.md` (why this
stack). If what actually gets built differs from this doc, this doc gets corrected
to match — it's not allowed to go stale.*

**Revised 2026-11-21, before any code existed**: the original version of this spec
was written when all three price sources were planned as simulated. Since then,
Sabre (flights) and Hotelbeds (hotels) were both registered for and confirmed
reachable with real data (`docs/NOTES.md` rounds 9–11). This revision updates
`sources/flights.py`, `sources/hotels.py`, the schema, and `config.py` to reflect
that — cabs remain simulated, unchanged, per `research_summary.md` §6.4/§7.3.

## Backend — `backend/app/`

| Module | Responsibility | Notes |
|---|---|---|
| `config.py` | Reads environment variables (DB connection string, app settings, Sabre and Hotelbeds credentials) into one typed `Settings` object | Single source of config; nothing else reads env vars directly. Needs `SABRE_TOKEN_URL`/`SABRE_BASE_URL`/`SABRE_USER_ID`/`SABRE_PASSWORD`/`SABRE_PCC`, `HOTELBEDS_BASE_URL`/`HOTELBEDS_HOTEL_API_KEY`/`HOTELBEDS_HOTEL_SECRET` |
| `database.py` | Creates the SQLAlchemy engine + session, and a `get_db()` dependency FastAPI routes use to get a DB session per request | Postgres connection lives only here |
| `models.py` | The 5 SQLAlchemy tables V1 needs: `User`, `TripRequest`, `PriceObservation`, `Notification`, `BookingAttempt` | Exact columns below in §1 |
| `schemas.py` | Pydantic request/response shapes for the API (what a client sends to create a request, what a check/booking response looks like) | Keeps API payload shape separate from DB model shape |
| `sim_clock.py` | `SimClock` — a single object the whole app asks for "now" instead of calling the system clock. V1: real-time only, `get_now()` reads the system clock; a `set_now()` exists but is just stored (not yet consumed anywhere, since nothing in V1 does time-based expiry) | Deliberately minimal in V1 — see `V1.md` §8 |
| `sim_controller.py` | In-memory store of per-request, per-component price overrides (`{(request_id, component): price}`), set via the Lab API and read by `pricing.py` — overrides apply on top of whatever a real or simulated source returned | Clears on process restart — acceptable for V1, since persistence-across-restart is a V2+ concern tied to real failure scenarios |
| `sabre_client.py` | `get_sabre_token()` — fetches a bearer token via Sabre's double-base64 client-credentials scheme and **caches it in memory for its 7-day lifetime** (never re-authenticate per price check); `search_flights(origin, destination, date, adults)` — calls Bargain Finder Max v4 (`POST /v4/offers/shop`) with the `POS`/`PCC` block, returns the raw parsed JSON | Confirmed working, round 9 (`docs/NOTES.md`). Token caching matters for respecting Sabre's own usage expectations, not just convenience |
| `hotelbeds_client.py` | `sign_request()` — `SHA256(apikey + secret + unix_timestamp)` per call (can't be cached, timestamp-based); `search_hotels(destination_lat, destination_lon, checkin, checkout, rooms, adults)` — calls `POST /hotel-api/1.0/hotels` with a `geolocation` block (not a destination code lookup — round 11 found codes aren't guessable, and geolocation search is what actually worked), returns the raw parsed JSON | Confirmed working, round 11. Goa's coordinates (15.2993, 74.1240) and Jaipur's are hardcoded constants here — no content-API destination lookup call is made at runtime, to protect the 50/day quota |
| `sources/flights.py` | `get_flight_prices(trip_request) -> dict` — calls `sabre_client.search_flights` for outbound and return legs separately, extracts `baseFareAmount`/`baseFareCurrency` (already INR directly in Sabre's response, no conversion needed — confirmed round 9) from the cheapest bookable itinerary, returns `{price, currency, status: "complete", source: "real-sandbox:sabre-bfm-v4", raw: <full response>}` | If the Sabre call fails or returns no itineraries, returns `status: "unavailable"` instead of a zero price (§05's explicit rule) |
| `sources/hotels.py` | `get_hotel_price(trip_request) -> dict` — calls `hotelbeds_client.search_hotels` for the trip's destination, picks the cheapest room matching the requested occupancy/star minimum, multiplies/validates against nights × rooms, converts EUR→INR using one documented fixed rate constant, returns `{price_inr, price_eur, conversion_rate, status: "complete", source: "real-sandbox:hotelbeds", currency_note: "approximate — EUR-sourced, converted at a fixed documented rate", raw: <full response>}` | **Currency confirmed EUR, round 13** (`CheckRates` call explicitly returned `"currency": "EUR"` — not a guess). Applying a documented, labeled conversion rather than marking this `provisional`, specifically because `provisional` would mean a hotel-containing package could never be `complete`, which would silently break V1's own happy-path alert demo. If the Hotelbeds call fails entirely or returns no hotels, returns `status: "unavailable"` instead — `provisional`/`unavailable` stay reserved for genuine data gaps, not this now-resolved unit-conversion question |
| `sources/cabs.py` | `get_cab_prices(trip_request) -> dict` — simulated fixed-quote price per transfer leg (airport→hotel, hotel→airport), modeled as a Kiwitaxi/Savaari-shaped fixed quote (not a surge multiplier, per round 4), **with vehicle class selected by adult count** (round 5): a sedan-class flat quote for ≤3 adults, a larger-vehicle quote anchored to the real ₹20–28/km tempo-traveller market range (round 5) for 4+ adults — so User B's 4-adult case gets a different, larger-capacity vehicle priced differently, not the same flat rate as User A/C | Labeled `source: "simulated"`, `status: "complete"`; this is the one component where V1's logic already has to satisfy §05's "cab passenger/luggage capacity" rule, not defer it |
| `pricing.py` | `build_package(trip_request, db) -> PackageResult` — calls all three source modules, applies any active `sim_controller` override, sums into an itemized total, and tags the whole package `complete` only if every component is `complete` — a package with the hotel's current `provisional` status is itself `provisional` (can't trigger a budget alert, per §05: "only complete, sufficiently fresh packages can trigger a budget alert") | This is the one function every endpoint below calls; it is the pricing engine itself. Also persists each component's full `raw` payload onto the `PriceObservation` row it creates (see §1) |
| `routers/users.py` | `GET /api/users` — lists the seeded mock users | Powers the mock-user switcher |
| `routers/requests.py` | `POST /api/requests` (create), `GET /api/requests?user_id=` (list, scoped to owner), `GET /api/requests/{id}` (detail) | Ownership scoping enforced here: every list/detail call filters by `user_id` |
| `routers/check.py` | `POST /api/requests/{id}/check` — runs `pricing.build_package`, stores a new `PriceObservation` row, and if this is the **first** observation ever under budget for this request, creates a `Notification` | The one-notification-only rule is a deliberate V1 simplification of the real §07 state machine, which is V2's job |
| `routers/notifications.py` | `GET /api/notifications?user_id=` (list, scoped), `POST /api/notifications/{id}/review` — re-runs `pricing.build_package` fresh (this is the "opening an old alert shows current validity" behavior, done simply) | Returns both the original alerted total and the freshly re-checked total so the frontend can show the delta |
| `routers/booking.py` | `POST /api/requests/{id}/book` — takes the just-reviewed total, "books" all three components (generates a fake supplier reference per component, e.g. `SIM-FLIGHT-xxxxx`), and stores one `BookingAttempt` row with all three component statuses set to `confirmed` and an aggregate status of `confirmed` | Happy path only — no failure branch exists yet; the aggregate-status field exists now specifically so V2 has somewhere to put `partial` later without a schema change |
| `routers/lab.py` | `GET /api/lab/clock` (current sim time), `POST /api/lab/override` (`request_id`, `component`, `price` → stored in `sim_controller`), `POST /api/lab/reset` (clears all overrides) | Everything here is explicitly dev/demo-only — never called by the real user-facing screens |
| `main.py` | Creates the FastAPI app, registers all routers, enables CORS for the frontend's local dev origin | The entry point (`uvicorn app.main:app`) |

**§1 — the 5 tables, columns:**

- `users`: `id`, `name` (e.g. "User A")
- `trip_requests`: `id`, `user_id` (FK), `origin`, `destination`, `outbound_date`, `return_date`, `adults`, `rooms`, `budget_inr`, `max_stops_outbound`, `max_stops_return`, `min_star_rating`, `checked_baggage` (bool), `status` (`active` only is used in V1; `paused`/`cancelled` exist as valid values for schema-forward-compatibility with V3, not acted on yet)
- `price_observations`: `id`, `request_id` (FK), `observed_at`, `flight_outbound_price`, `flight_return_price`, `flight_status`, `hotel_total_price`, `hotel_status`, `cab_outbound_price`, `cab_return_price`, `cab_status`, `taxes_fees`, `total_price`, `status` (package-level: `complete`, `provisional`, or `unavailable` — `complete` is the expected status for a normal V1 check now that the hotel currency question is resolved; `provisional`/`unavailable` are reachable if a real call to Sabre or Hotelbeds fails or returns nothing, not from the now-settled currency question), `raw_sources` (JSONB — the full raw flight/hotel API response(s) this observation was built from, for traceability and §14's data-source dossier; `null` for the simulated cab component)
- `notifications`: `id`, `request_id` (FK), `observation_id` (FK), `created_at`, `reviewed_at` (nullable)
- `booking_attempts`: `id`, `request_id` (FK), `notification_id` (FK), `created_at`, `accepted_total`, `flight_status`, `hotel_status`, `cab_status`, `aggregate_status`, `supplier_ref_flight`, `supplier_ref_hotel`, `supplier_ref_cab`

## Backend — `backend/scripts/`

| Module | Responsibility |
|---|---|
| `seed.py` | Creates the tables (if not present) and inserts User A with the exact request from the assignment's §02 table (Mumbai⇄Goa, 2 adults, 3 nights, 1 room, ₹35,000) |
| `reset.py` | Drops and recreates all tables, then calls `seed.py` — the literal "reset" half of §11's "reset and replay" requirement, minimal version |

## Backend — root files

| File | Responsibility |
|---|---|
| `requirements.txt` | `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2-binary`, `pydantic`, `python-dotenv`, `httpx` (for real Sabre/Hotelbeds calls) |
| `.env.example` | `DATABASE_URL=postgresql://user:password@localhost:5432/tavora`, plus placeholder (no real values) entries for every `SABRE_*`/`HOTELBEDS_*` key named in `config.py` above |
| `README.md` | How to install, set up Postgres locally, run migrations/seed, and start the server |

## Frontend — `frontend/src/`

| Module | Responsibility |
|---|---|
| `api.ts` | Thin wrapper around `fetch` for every backend endpoint above — the only file that knows the API's URLs | |
| `App.tsx` | Top-level router (React Router): routes to each page below, plus a persistent mock-user switcher in the header | |
| `pages/RequestForm.tsx` | The create-request screen — all of §03's fields | |
| `pages/Dashboard.tsx` | Lists the current user's requests; a "Check price now" button per request; shows the latest observation's itemized total | |
| `pages/Notifications.tsx` | Lists the current user's notifications; opening one calls `review`, shows original vs. revalidated total | |
| `pages/OfferReview.tsx` | Shows the revalidated itemized package; a "Confirm booking (simulated)" button, clearly labeled | |
| `pages/BookingResult.tsx` | Shows the booking attempt: each component's status + supplier reference, and the aggregate status | |
| `pages/Lab.tsx` | The Scenario Lab — V1 version: current sim time display, a form to set a price override for a request/component | |
| `styles.css` | One shared stylesheet; deliberately plain — §10/§15 both say UI polish is the lowest priority | |

## Frontend — root files

| File | Responsibility |
|---|---|
| `package.json` | React, react-dom, react-router-dom, typescript, vite | |
| `vite.config.ts` | Standard Vite+React+TS config, dev server proxying `/api` to the backend | |
| `tsconfig.json` | Standard strict TS config | |
| `index.html` | Vite entry HTML | |

## Build order (so nothing gets built out of dependency order)

1. `config.py` → `database.py` → `models.py` (nothing else can work without these)
2. `sabre_client.py`, `hotelbeds_client.py` (standalone API clients, no app dependencies) → `sources/*.py` → `pricing.py` (the pricing engine needs the sources to exist first)
3. `sim_clock.py`, `sim_controller.py` (small, independent, needed by `pricing.py` for overrides and by `routers/lab.py`)
4. `schemas.py` → all of `routers/*.py` → `main.py`
5. `scripts/seed.py` / `reset.py`
6. Frontend, page by page, in the same order a user would move through the app:
   `RequestForm` → `Dashboard` → `Notifications` → `OfferReview` → `BookingResult` →
   `Lab`

## Built / matches spec (2026-11-21)

All backend modules listed above are built and match this spec, with one
deliberate addition made during implementation: `sabre_client.py` and
`hotelbeds_client.py` exist as their own files (named in the "Built / matches
spec" build order above too), separating "talk to this specific supplier" from
"decide what price to report" in `sources/*.py` - a one-file split that wasn't
written into the table above in so many words but follows directly from it.

**Verified by a real, live end-to-end run** (not just unit-level): seeded the
database, started the server, and called the real sequence a user would -
create implied by seed, `check` (real Sabre + real Hotelbeds + simulated cab,
itemized total ₹34,559.65 under User A's ₹35,000 budget), confirmed exactly one
notification was created, `review` (re-checked fresh, deterministic Sabre/
Hotelbeds test-cell data returned the same total), `book` (all three components
confirmed with distinct fake supplier references). Also verified: the raw
Sabre/Hotelbeds responses are actually persisted on the `PriceObservation` row
(`raw_sources`), a Lab price override actually changes what `check` returns,
`/api/lab/reset` clears it, and ownership scoping actually blocks User B from
reading User A's request by ID.

Frontend (`frontend/src/*`) has not been built yet - that's the next step per
the build order above.
