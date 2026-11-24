# Requirements gap tracker — working document

Purpose: a single place tracking every requirement in `docs/assignment.pdf` against its real, verified
implementation state, so nothing gets lost across sessions/compaction. This is a **working/local
document**, not a polished deliverable — updated in place as we go, not regenerated from scratch.

Last updated: 2026-11-24 (mid-audit — four verification passes in flight, results being filled in below
as they land).

Status legend: ✅ done & verified · 🟡 partially done (see notes) · ❌ not done · 🔎 verifying now

---

## 02 — Required demonstration requests
Three mock users seeded with the exact routes/travellers/budgets specified.
Status: ✅ (verified live via API earlier this session — User A/B/C, correct routes/budgets)

## 03 — Request inputs and scope
Create/edit with all specified fields; INR/adults only; mock-user switcher; ownership scoping;
pause/cancel; edit invalidates obsolete offers.
Status: 🔎 verifying — user disputes that editing actually changes anything observable, and wants a
much more "real journey" presentation, not just raw fields. Pending: audit pass E (requests.py
`update_request` / `_invalidate_stale_offers`).

## 04 — Data sourcing
Real/sandbox retrieval where accessible (flights/hotels via Sabre/Hotelbeds); documented simulated
source where not (cabs); live/sandbox/synthetic clearly labelled; no static hardcoded price list.
Status: 🔎 verifying — user wants real-looking flight/hotel/cab **names and images**, and believes prices
barely change on active requests in practice. Pending: audit pass 1 (frontend/data realism) and pass 2
(price variation mechanism).

## 05 — Build comparable, feasible packages
Cheapest complete package from retrieved inventory; itemized breakdown; occupancy/baggage/taxes/cab
capacity/timezone/overnight handling; check-in/out + transfer-buffer assumptions explained; unknown
charges never silently zero; complete/provisional/unavailable labelling.
Status: 🔎 verifying — user says "we are not doing any of these or even trying to show it." Pending:
audit pass A.

## 06 — Monitor and keep an audit trail
5-minute cycle + manual check; documented scheduling strategy; persisted observation times/source
refs/prices/totals/failures; latest valid total, lowest observed valid total, price-history chart; no
constructed-from-minima packages; failed check never shows as zero or erases history.
Status: 🟡 mechanism exists (scheduler.py, monitoring.py, PriceObservation append-only rows, Dashboard
chart) — but user's core complaint is that **prices don't actually move over time in practice**, which
undermines the whole point of "monitoring." Pending: audit pass 2.

## 07 — Notify the matching traveller
First-crossing/5%-redrop/reset alert rule; in-app inbox; itinerary/itemized total/observation
time/quote status/Review & book action; dedup; old alert shows current validity.
Status: 🔎 verifying — user says "there is nothing like this too." Pending: audit pass B.

## 08 — Revalidate, hold and obtain consent
Fresh quote + recheck on open; price-change display; explicit accept; 2-min per-component hold;
package locked only while all holds valid; expiry = earliest component; release holds if package
can't be secured; held price preserved until expiry.
Status: 🔎 verifying — user says "we are not doing this either." Pending: audit pass C.

## 09 — Persist and recover the workflow
Six specific failure/recovery rows (dup confirmation, inventory/hold expiry, partial failure +
compensation, supplier timeout, app restart resume, cancellation failure → manual intervention).
Status: 🔎 verifying — user says "we have not tried to do any of these either." Pending: audit pass D.

## 10 — Minimum interface
Request create/edit; watch dashboard with current+historical totals; per-user notifications; offer
review with hold countdown; booking results; ops view for partial bookings + event timeline.
Status: 🟡 — pages exist per earlier work, but user considers the UI itself far below the bar needed to
actually *showcase* all of the above (no real page routing/slugs, "view journey" page considered
useless, no next/previous step-through, no real names/images). Note: assignment explicitly says "UI
polish is secondary to correct behavior" and this is only 5% of the grade — flagged as a real tension to
resolve with the user, not a decision to make unilaterally. Pending: audit pass 1.

## 11 — Repeatable scenario runner
Deterministic fixtures/controls for sim time, supplier prices, inventory exhaustion, failure injection;
7 named scenarios must each be demonstrable and resettable/replayable.
Status: 🔎 verifying — user calls the current Scenario Lab "horrible," wants proper logs (user, hotel
name, flight name, cab name, total cost, simulated/real, finished/unfinished, caching, duration).
Pending: audit pass "scenario runner" (per-scenario verdict + logging gap).

## 12 — Tests and performance evidence
Automated tests for the listed behaviors; a **reproducible 100-active-request / 3-cycle load
demonstration** with reported numbers; caching/source-limit/cost-at-1000 explanation.
Status: 🟡 47 backend tests exist and pass — but the **100-request load demonstration appears to not
exist at all**. Pending: audit pass "deliverables" confirms presence/absence + exact numbers if any.

## 13 — Live technical review
Not a build item — a readiness concern (can the candidate explain/trace/defend the work live). Noted
here only because it depends on everything above actually being true and understood, not just
written down.
Status: N/A for code, but highest-stakes item — depends on closing the real gaps above honestly.

## 14 — Deliverables
| Deliverable | Status | Notes |
|---|---|---|
| Code repository | ✅ | lockfiles, config example, schema/migrations, seed/reset scripts all exist |
| Runnable product | 🔎 verifying | live site reachable; user claims data "corrupted" — checking now |
| Methodology report | 🔎 verifying | `docs/METHODOLOGY_REPORT.md` exists — substance vs. filler unconfirmed |
| How-it-works guide | 🔎 verifying | user specifically disputes any real architecture/data-model/sequence/state diagrams exist |
| Data-source dossier | 🔎 verifying | `docs/DATA_SOURCE_DOSSIER.md` exists — substance unconfirmed |
| Verification package | 🔎 verifying | tests exist; load-demo + requirement-to-implementation checklist unconfirmed |
| Demo and handover | 🔎 verifying | `docs/DEMO_AND_HANDOVER.md` exists — substance unconfirmed |

---

## Open strategic tension (needs your decision, not mine to assume)
The assignment's own evaluation weights are **30% booking correctness/concurrency/recovery, 20%
source/data integrity, 20% monitoring/notification correctness, 15% tests/reproducibility, 10%
methodology/live understanding, 5% usability**, and says explicitly: *"A polished interface cannot
compensate for incorrect totals, duplicate bookings, misleading price locks or undocumented synthetic
data... Complexity and code volume do not earn credit by themselves."* That cuts against spending the
one day left mainly on a frontend rebuild (slugs/pagination/real images) rather than closing any real
gaps in sections 05/07/08/09/12/14 if those turn out to be real. I'm not deciding this for you — once
the four audits land I'll show you exactly what's real vs. missing, and we prioritize together against
the clock (deadline 2026-11-25).

## 🚨 ACTIVE PRODUCTION BUG (found during audit, 2026-11-24)
Every active request's hotel component has returned `hotel_status: "unavailable"` / `total_price: null`
on every real monitoring cycle since ~04:11 today, across all 3 users. Flight prices are returning
byte-identical values cycle to cycle (not a new issue, see below). An earlier observation this morning
shows hotel data working, so something broke mid-session — likely Hotelbeds sandbox
auth/signature/rate-limit. **Root cause not yet diagnosed.** This is almost certainly what the user saw
as "the data on the website has been corrupted and nothing is working."
Status: ❌ NEEDS IMMEDIATE FIX — this is live-demo-breaking right now, independent of any of the
longer-term scope questions below.

## Audit pass 1 — frontend UX / data realism / live-site health: COMPLETE
- Routing/slugs: user's complaint was **wrong** — real react-router paths exist (`/requests/:id/story`,
  `/offer/:notificationId`, `/booking/:bookingId`, etc.), confirmed in `App.tsx:60-71`.
- "Journey" page: **partially right** — real flight/hotel names/numbers/times ARE shown (from real
  Sabre/Hotelbeds sandbox data), but it's one long scrolling page, no next/previous step-through wizard.
  Legitimate gap: 🟡 missing pagination/step-through UX.
- Images: **confirmed absent** — zero `<img>`/background-image/image assets anywhere in `frontend/src/`.
  ❌ gap, if desired.
- Price variation: **user is right** — Sabre sandbox returns byte-identical flight prices across repeat
  calls for a fixed future date; cab price is a hardcoded constant (`SEDAN_FLAT_FARE = 900.0`); nothing
  varies on its own outside a manual Lab override. ❌ gap — "monitoring" currently has nothing real to
  monitor in day-to-day usage without the Lab.
- Live site: **confirmed actually broken** — see production bug section above.

## Audit pass 2 — scenario runner vs. the 7 required scenarios: COMPLETE
| # | Scenario | Verdict |
|---|---|---|
| 1 | Below-budget trip | ✅ fully supported, real end-to-end path |
| 2 | Price changes before review | ✅ fully supported |
| 3 | Hold validity and expiry | ✅ fully supported (sim_clock fast-forward) |
| 4 | Last room contention | ❌ **structural gap** — no shared/finite inventory concept exists anywhere; genuinely not possible to demonstrate today without adding one |
| 5 | Partial booking failure | ✅ fully supported |
| 6 | Timeout and restart | ✅ fully supported |
| 7 | Monitoring reliability | ✅ fully supported |

Logging/history: **confirmed absent** — Lab.tsx is nine one-shot control forms + one transient message
string that gets overwritten. No persisted log of past actions, no user/hotel/flight/cab names, no
cost, no simulated-flag, no duration, no finished/unfinished state anywhere. This is a real gap matching
the user's complaint.

## Audit pass 4 — sections 05/07/08/09 + edit-invalidation code-level verdicts: COMPLETE

**Sec. 05 (package search/ranking) — 🟡 PARTIALLY TRUE claim, real but materially incomplete:**
- Itemized total, complete/provisional/unavailable labelling, never-silent-zero on failure: ✅ real
  (`pricing.py::build_package`, `flights.py:62`, `hotels.py:62-67`).
- ❌ `max_stops_outbound`/`max_stops_return` and `checked_baggage` are stored on every request and
  exposed in the API, but **never actually read anywhere in pricing or source code** — confirmed via
  grep, zero hits outside models/schemas. These stated request constraints currently do nothing.
- ❌ Hotel pricing takes the cheapest eligible room rate but does **not multiply by `trip_request.rooms`**
  — User B's 2-room request is priced as if for 1 room. This is a real pricing-correctness bug.
- ❌ `validation.py`'s own docstring claims to implement "check-in/check-out/transfer-buffer
  assumptions" per Sec. 05, but the function only checks `return_date > outbound_date` — no
  timezone/overnight/buffer logic exists at all. The doc comment overclaims what the code does.

**Sec. 07 (notifications) — ❌ user's "there is nothing like this" claim is FALSE.** Real and reasonably
complete: itinerary/itemized total/quote status/observation time all returned
(`notifications.py:30-53`); opening an old alert runs a genuinely fresh check
(`review_notification`, line 87) — this literally is "opening an old alert shows current validity."

**Sec. 08 (hold/revalidation) — 🟡 PARTIALLY TRUE, one real spec deviation worth knowing about.**
Fresh-quote-on-open and hold-expiry enforcement are real, not stubs (`notifications.py:87-104`,
`booking.py:212-229`). But the spec asks for **a hold per component** (package locked only while ALL
component holds are valid, expiry = earliest component expiry); the real implementation holds the
**whole package as one unit** against a single `held_until` on the Notification. Works correctly for
every demo scenario, but is a simplification of the literal spec, and isn't explicitly flagged anywhere
as "this guarantee is simulated as one unit, not per-component" (Sec. 08 explicitly asks for that kind
of disclosure).

**Sec. 09 (failure/recovery) — ❌ user's "we have not tried to do any of these" claim is FALSE, and this
is the most solid part of the whole backend.** All six required rows verified with real code: idempotency
(DB unique constraint + IntegrityError race handling), hold-expiry rejection, partial-failure
compensation, supplier-timeout → blocked-until-reconcile, app-restart resume, cancellation-failure →
manual_intervention (never silently marked cancelled). Don't let this complaint stand — it's wrong.

**"Editing doesn't change the total" — ❌ FALSE as a backend claim, but real UX gap behind it.**
`update_request` does invalidate stale holds, reset `last_alerted_total`, bump `updated_at`
(`requests.py:97-108`); Dashboard does show a stale-total banner off that. The mechanism works. Likely
driver of the complaint: editing does **not** trigger an immediate re-check — the number on screen
stays the old one (now marked stale) until the next 5-min cycle or a manual check. If the stale-total
banner isn't obviously visible in the live UI, "it still doesn't change" is an accurate *impression* even
though the backend state is correct. Worth a visual check.

## Next update
Will be filled in when the last audit pass completes:
3. Deliverable docs substance (diagrams, load-test, checklist) — pending
