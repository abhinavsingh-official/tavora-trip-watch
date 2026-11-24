# Final push plan — 2026-11-24/25, submission day

Working execution checklist, updated in place as we go (not regenerated from scratch). Backing
evidence for every claim below is in `docs/internal/requirements-gap-tracker.md`.

**Guiding principle, re-read this before every decision today:** a reviewer has minutes, not hours, and
will not read source code. Correct-but-invisible is worth zero. Priority order: (1) nothing visibly
broken, (2) the real backend logic becomes watchable without narration, (3) real correctness bugs
fixed, (4) the product looks and feels like something alive, not a form.

Status legend: [ ] not started · [~] in progress · [x] done

---

## Phase 0 — Docs hygiene (quick, do first)
- [ ] 0.1 Create `docs/internal/` — move everything that isn't one of the 6 official deliverables there,
      with clean lowercase-hyphen names:
      - `DECISIONS.md` → `internal/decision-log.md`
      - `NOTES.md` → `internal/research-notes-raw.md`
      - `research_summary.md` + `Tavora_Research_Summary.pdf` → check for duplication, consolidate to
        one `internal/research-summary.md`
      - `SIMPLE_PLAN.md` + `Trip_Price_Watch_Simple_Plan.pdf` → archive if superseded, else
        `internal/early-plan.md`
      - `UI_PLAN.md` → `internal/ui-plan.md`
      - `AUDIT_2026-11-23.md` → `internal/audit-log-2026-11-23.md`
      - `REQUIREMENTS_GAP_TRACKER.md` → `internal/requirements-gap-tracker.md`
      - `CODE_WALKTHROUGH.pdf`, `TABLE_METHODOLOGY_AND_CODE_REUSE.pdf` → `internal/`
      - `versions/` folder stays, already well-named (V1–V7.md)
- [ ] 0.2 Root `docs/` ends up containing only: `METHODOLOGY_REPORT.md`, `HOW_IT_WORKS.md`,
      `DATA_SOURCE_DOSSIER.md`, `VERIFICATION_PACKAGE.md`, `DEMO_AND_HANDOVER.md`, `assignment.pdf`,
      `ui_references/`, `versions/`
- [ ] 0.3 Fix any now-broken internal links between docs after the move

## Phase 1 — Data layer: real hotels pre-fetched, synthetic flights, synthetic cabs
- [x] 1.1 Use the fallback Hotelbeds account for a one-time bulk pre-fetch — done via
      `backend/scripts/fetch_hotel_directory.py`, 3 real calls (one per demo user's exact search key),
      disclosed as a one-time seed fetch, not routine quota-doubling
- [x] 1.2 Real hotel counts achieved: **48** for User A, **47** for User B, **20** for User C (115 total)
      — exceeds the ~30-per-user target for 2 of 3; see note below on why B started at only 5
- [x] 1.3 New table `CachedHotelOption` — destination/dates/occupancy search key, real hotel name, star
      rating, room description, EUR price, fetched-at, source tag
- [x] 1.4 `hotels.py::get_hotel_price` and new `get_hotel_candidates` read this cache first; live
      Hotelbeds call (primary account) kept as fallback for any search key not cached, never fabricates
      a price if that also fails
- [x] **Real bug found and fixed along the way, not originally on this list:** Hotelbeds' `occupancies`
      field needs one entry per room (each with its own adults count), not one combined entry with
      `rooms` as a multiplier. The combined shape silently starved multi-room searches of real inventory
      (User B's exact search went from 5 priced hotels → 47 once fixed, and her hotel total went from a
      budget-breaking ₹97,535 to a real ₹11,850 for 2 rooms). Fixed in `hotelbeds_client.py` and
      `sources/hotels.py`; full detail in `docs/internal/requirements-gap-tracker.md`'s correction note.
      This also means the earlier "room-count multiplier bug" finding from the original audit was wrong
      — no separate fix needed for that; removed from Phase 2.
- [ ] 1.5 Build the synthetic flight generator: same real shape Sabre already gave us (airport codes,
      realistic carriers/flight numbers/timings for the actual routes), producing a larger directory
      (10+ options per leg) per request — clearly labeled synthetic in the UI and docs
- [x] 1.6 Sabre's real integration stays in the codebase/dossier as proof of real access; the live
      product's flight data now comes from `SyntheticFlightOption` instead (same real route/airport
      shape, mutated over time), with a live Sabre call kept as the fallback for any uncached search key
- [x] 1.7 Synthetic cab directory built: 4 vehicle classes (2 sedans, 1 SUV, 1 tempo traveller), vendor
      name, passenger/luggage capacity, per-leg price anchored to the real RTO rate cards already
      documented — `sources/cabs.py` now genuinely rejects a party too large or too much baggage for
      every available class, verified by test
- [x] 1.8 `app/price_mutation.py::mutate_all_prices` nudges every synthetic flight/cab price and the
      cached real hotel price by a small bounded random step (clamped to ±30% of each row's own base,
      verified by test to hold even after 200 repeated mutations) — wired into `scheduler.py::run_one_cycle`
      so every real 5-minute cycle drifts prices before checking them, no manual step required
- [x] 1.9 `POST /api/lab/mutate-prices` — a nudge-only endpoint distinct from trigger-cycle (which
      mutates AND checks/alerts in one step), so a demo can nudge prices a few times first, then trigger
      a check separately
- [x] 1.10 `DATA_SOURCE_DOSSIER.md` updated: synthetic flight generator, the real hotel cache + fallback
      account disclosure, the occupancy-payload bug, the cab directory redesign, and the new §7
      price-mutation section — all cross-referenced. `decision-log.md` also got 3 new entries for this
      phase's real findings (occupancy bug, synthetic-directory decision, price-mutation rationale).

**Phase 1 status: complete.** All of 1.1–1.10 done, including the real occupancy-payload bug fix (not
originally planned) and folding Phase 2's 2.1–2.5 in alongside it since the same files were already
open. 53/53 backend tests passing (47 original + 6 new, covering cab capacity rejection, flight
max-stops filtering, per-adult flight pricing, and the baggage fee).

## Phase 2 — Real correctness fixes (Sec. 05's own checklist, actually enforced in code)
- [x] ~~2.1 Fix hotel pricing: multiply per-room rate by rooms~~ — resolved in Phase 1; the real bug was
      the occupancy payload shape, not missing multiplication (see Phase 1 note above)
- [x] 2.2 `max_stops_outbound`/`max_stops_return` now filter real flight candidates (`flights.py`'s
      `_cached_leg_candidates`) — verified by test, a cheaper option exceeding the limit is excluded
      entirely, not just deprioritized
- [x] 2.3 `checked_baggage` now drives real cab eligibility (luggage capacity, `cabs.py`) and a flat,
      documented per-adult/per-leg flight baggage fee (`pricing.py`'s `CHECKED_BAGGAGE_FEE_PER_ADULT_PER_LEG`)
      — both verified by test
- [x] 2.4 Adult-fare accounting fixed to be genuinely per-adult for flights (`SyntheticFlightOption`
      stores a per-adult base price, multiplied by the real adult count at read time — previously the
      real Sabre anchor numbers were silently treated as flat group totals); hotels were already
      correctly occupancy-priced once the 1.1–1.4 payload fix landed
- [x] 2.5 Taxes/mandatory charges: 5% flat tax plus the new baggage fee now both fold into the
      `taxes_fees` field, which the code and `METHODOLOGY_REPORT.md` should describe as "taxes AND
      mandatory charges combined," not tax alone — reflect this wording when Phase 5 updates that doc
- [x] 2.6 New `app/schedule_rules.py`: standard check-in 14:00 / check-out 11:00, 45-min transfer buffer
      (anchored to cabs.py's existing 30km assumed leg distance, not a separate guess). Outbound
      candidates arriving after 23:00 and return candidates departing before 11:45 are now excluded
      entirely from `flights.py`'s candidate selection — verified by 2 new tests; confirmed none of the
      3 real demo users' legs lose all their candidates (all still price `complete`, under budget)
- [x] 2.7 Airport codes confirmed correct for all 3 routes: BOM/GOI (Mumbai/Goa, real, already verified
      against a live Sabre call), DEL (Delhi), JAI (Jaipur) — both standard, unambiguous real IATA codes,
      no GOA/GOI-style gotcha like the one hotels.py's destination search already found and documented
- [ ] 2.8 Hold model: **deferred, not re-architected** — whole-package hold stays as-is given everything
      else outstanding; to be explicitly disclosed as a documented simplification in
      `METHODOLOGY_REPORT.md` during Phase 5, per Sec. 08's own "explain which guarantees exist only in
      your simulation" ask
- [x] 2.9 New tests added: cab capacity/baggage rejection (3), flight max-stops filtering (1), per-adult
      flight pricing (1), baggage fee (1), transfer-buffer exclusion outbound/return (2) — 8 new tests
      this phase, 55/55 total passing
- [x] 2.10 Full backend test suite green (55/55); real 3-demo-user end-to-end check re-verified after
      the buffer rule landed

## Phase 3 — Scenario Lab: make the real logic watchable
- [ ] 3.1 Persisted log of what happened: timestamp, user, route, component names (now real-feeling
      flight/hotel/cab names from the new data layer), total cost, real/simulated tag, status
      (finished/failed/unfinished), duration
- [ ] 3.2 Every Lab action and every real scheduler/booking event writes a log entry
- [ ] 3.3 Backend endpoint: list the log (recent-first), clear-log action
- [ ] 3.4 Redesign `Lab.tsx`: visible running log in plain language, not one disappearing message
- [ ] 3.5 Map each of the 7 required demo scenarios to one named, one-click flow in the Lab UI
- [ ] 3.6 Build the minimal real version of scenario 4 (last-room contention): a finite simulated room
      count on one hotel+date in the new cached-hotel data, decremented atomically on booking, a Lab
      control to set "rooms remaining," so two users can actually race for it
- [ ] 3.7 Test: scenario 4 actually produces one winner, one real rejection, not a crash

## Phase 4 — Frontend: feel like a real product
- [ ] 4.1 One consistent visual system (palette/type/spacing/cards) applied everywhere
- [ ] 4.2 "Trip Price Watch" in the top nav becomes a real link to Home
- [ ] 4.3 Persistent sidebar showing the current user
- [ ] 4.4 Stock images (hotels/flights/cabs) from a free no-attribution source, clearly disclosed as
      decorative stock imagery, wired into hotel/flight/cab cards, home page, dashboard
- [ ] 4.5 Dashboard redesign: prominent fluctuation chart, lowest-ever total, latest total, budget
      comparison, clear status badges — reads as a dashboard, not a plain list
- [ ] 4.6 "Recommended next trip" widget, clearly labeled illustrative
- [ ] 4.7 Rename/restyle "Trip Story" → "Your Bookings": multi-page step-through (hotels → flights →
      cabs, next/previous), each page lets the reviewer sort/browse the real directory (now ~30 hotels,
      10+ flights, 2–3 cabs) and swap the current pick for another
- [ ] 4.8 "Pay" button at the end of that flow finalizes the existing simulated booking immediately,
      explicitly labeled "Simulated purchase — no real payment processed"
- [ ] 4.9 Per-user "Return to default" button/page: only appears if that user's requests differ from
      their original seed values; resets back to seed state on click (new backend endpoint)
- [ ] 4.10 Full manual click-through of every page after the redesign

## Phase 5 — Docs, re-verification, close-out
- [ ] 5.1 Update `METHODOLOGY_REPORT.md` / `HOW_IT_WORKS.md` / `DATA_SOURCE_DOSSIER.md` for everything
      in Phases 1–4
- [ ] 5.2 Re-run the 100-request/3-cycle load test, update numbers in `VERIFICATION_PACKAGE.md`
- [ ] 5.3 Update the requirement checklist in `VERIFICATION_PACKAGE.md` to reflect the real new state
- [ ] 5.4 Full backend test suite + frontend build, clean
- [ ] 5.5 Final live-site walkthrough across every page, including new ones
- [ ] 5.6 PR(s) opened per logical chunk, branch → PR → your review/merge, as always
- [ ] 5.7 You do your own full read-through and multiple live runs — we stop when you're confident, not
      when the checklist is empty

---
## Status
Not started — execution begins now.
