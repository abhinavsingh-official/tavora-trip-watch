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
- [ ] 1.1 Use the fallback Hotelbeds account (`HOTELBEDS_FALLBACK_HOTEL_API_KEY`/secret) for a one-time
      bulk pre-fetch — real API, real data, separate already-issued credential, used once for seeding
      (disclosed explicitly in the dossier as "fallback account, one-time seed fetch, not routine
      quota-doubling")
- [ ] 1.2 Widen search radius/params as needed to pull ~30 real hotels for Goa and ~30 for Jaipur in as
      few calls as the API allows (likely 1–2 calls per destination based on the real response shape
      already confirmed)
- [ ] 1.3 New table: `CachedHotel` (or similar) — destination, real hotel name, star rating, per-night
      rate(s), room occupancy fit, sourced-from-real flag, fetched-at timestamp
- [ ] 1.4 `hotels.py` reads from this cache for the live product instead of calling Hotelbeds per check;
      keep the real live-call path available/documented, just not on the hot path anymore
- [ ] 1.5 Build the synthetic flight generator: same real shape Sabre already gave us (airport codes,
      realistic carriers/flight numbers/timings for the actual routes), producing a larger directory
      (10+ options per leg) per request — clearly labeled synthetic in the UI and docs
- [ ] 1.6 Keep Sabre's real integration in the codebase and documented in the dossier as proof of real
      access/research — note explicitly that the live product's actual flight data comes from the
      synthetic generator instead, and why (static test-cell fares can't demonstrate monitoring)
- [ ] 1.7 Build the synthetic cab directory: 2–3 vehicle classes (sedan/SUV/tempo), vendor name,
      passenger capacity, luggage capacity, per-leg price anchored to the real RTO rate cards already
      documented — reject combinations where `adults` exceeds passenger capacity or `checked_baggage`
      exceeds luggage capacity
- [ ] 1.8 Price-mutation script: perturbs the stored synthetic flight/hotel/cab prices slightly over
      real time (seeded/deterministic, replayable) so monitoring looks alive without manual
      intervention
- [ ] 1.9 Manual toggle in the Scenario Lab to force an immediate price change on demand, for live-demo
      pacing (since real elapsed time may not cooperate during a review session)
- [ ] 1.10 Update `DATA_SOURCE_DOSSIER.md`: disclose the synthetic flight generator, the cab directory
      design, the fallback-account one-time use, and the price-mutation/toggle mechanism — what's real,
      what's synthetic, why, exactly per Sec. 04's own disclosure requirement

## Phase 2 — Real correctness fixes (Sec. 05's own checklist, actually enforced in code)
- [ ] 2.1 Fix hotel pricing: multiply per-room rate by `trip_request.rooms` (hits User B directly)
- [ ] 2.2 Wire `max_stops_outbound`/`max_stops_return` into real flight filtering (currently unused)
- [ ] 2.3 Wire `checked_baggage` into real flight pricing/filtering (currently unused) and into the new
      cab capacity rejection (1.7)
- [ ] 2.4 Confirm/fix adult-fare accounting is actually per-adult, not flat, across flights and hotels
- [ ] 2.5 Confirm the 5% flat tax adequately represents "taxes, mandatory charges," or itemize further
      if the assignment's own wording implies more granularity is expected
- [ ] 2.6 Build real check-in/check-out/overnight-travel/timezone/transfer-buffer logic (currently
      doesn't exist at all) — define the assumptions explicitly in `METHODOLOGY_REPORT.md`, reject
      combinations that violate them (e.g., arrival after midnight without buffer for hotel check-in)
- [ ] 2.7 Confirm airport-identity handling is correct for all 3 routes (BOM/GOI, DEL/GOI, BOM/JAI or
      equivalent real codes)
- [ ] 2.8 Decide + implement or explicitly document: whole-package hold (current, simpler) vs. real
      per-component hold expiry — lower priority than everything else in this phase, do last if time
      allows, otherwise disclose the simplification clearly per Sec. 08's own ask
- [ ] 2.9 New/updated automated tests for every fix above
- [ ] 2.10 Full backend test suite green

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
