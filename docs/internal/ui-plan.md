# UI / Polish Plan — working notes

*Living document for the UI pass that comes after V4. Unlike `docs/versions/
*.md`, this isn't a record of something shipped — it's where the plan lives
while it's still being decided, so a conversation doesn't become the only
place it's written down. Once this pass actually ships, its real content
moves into a new `docs/versions/V5.md` (or whichever version number it
ends up being), same as every prior version.*

## Status (as of 2026-11-23)

**Shipped as V5** - see `docs/versions/V5.md` for the full record (what
changed, what was tested, two real bugs found and fixed along the way).
This document's planning content below is kept as-is for context on *why*
V5 looks the way it does; nothing further is pending from this round.

The candidate asked directly to implement "every change we talked about
before and the UI changes fully" before personally reviewing the result -
so this was built from the plan below (the lighter approach, the real
frontend reference survey) rather than from a separate itemized list.
Whatever the candidate finds on their own pass through the live result is
the next round, not a continuation of this one.

## Open product-framing question — now resolved

**The question, as raised**: the brief was read as asking for "a general
website for booking AND a simulation," and the current build "feels like
just a normal simulation."

**Checked against the brief's own wording** (`docs/assignment.pdf` §01/§03):
this is one real product (real request creation, real monitoring, real
alerts, real hold/review flow) where only the final booking *action* is
simulated, by explicit instruction - *"All booking actions must be clearly
labelled as simulated"* and *"This is a single feature prototype, not a
rebuild of Tavora... Real purchases, real payment collection and production
customer data are outside scope."* So the brief itself does not ask for two
separate things (a real booking website + a separate simulation) - it asks
for one product whose one clearly-labeled step is simulated. This reading
was shared back and the candidate agreed.

**A specific idea was floated and considered, then set aside**: a locked,
non-interactive "replay" mode - click through pages exactly like watching
someone else's real booking happen on their PC, pre-selected and
unchangeable - with an explicit "Custom/Simulation" toggle to switch into
the real interactive product (pick mock user A/B/C, or start from scratch).

**Decision: not doing the locked-replay mode. Doing the lighter version
instead.** Reasoning, recorded here so it isn't re-debated later without
cause:
- It's a second UI mode on top of the real one - meaningfully more build
  risk than "polish the existing pages," with little runway left before
  the 2026-11-25 deadline.
- The brief weights usability at only 5% and says explicitly that "UI
  polish is secondary to correct behavior" and "complexity and code volume
  do not earn credit by themselves" (§10/§15).
- A locked/read-only default view risks friction during the live technical
  review (§13), where the reviewer needs to actually trace a request,
  diagnose a failure, and handle an on-the-spot rule change - not watch a
  recording first.

**What "the lighter version" means, concretely** (the plan, not yet built):
- Keep one real, interactive product - no separate replay/viewer mode.
- Make the existing pages look and flow like a real booking site (proper
  step-based layout, consistent visual language) rather than raw forms.
- Get the "feels like watching someone's real booking" effect for free: the
  user switcher already lands on A/B/C's real, already-seeded data - no
  special non-editable mode needs to be built to get that impression.

## Other known UI items to fold into the batched pass

- **Scenario Lab wording is "worded weirdly"** (candidate's words) -
  **done as part of V5**: full copy rewrite, one shared target-request
  field instead of four duplicated ones, "Arm X" renamed to "Schedule X"
  throughout. See `docs/versions/V5.md` §2.
- Whatever else the candidate's own stress-testing and doc review surfaces
  from here - a new round, not a continuation of this one.

## Real frontend reference survey (2026-11-23)

Real, live screenshots (not descriptions from memory) of four sites, taken
headlessly and reviewed directly, to pull concrete layout/interaction
patterns from before any redesign work starts. Images are in
`docs/ui_references/`. Two targets (Goibibo, MakeMyTrip) were blocked by
anti-automation measures and are skipped rather than faked; ixigo returned a
rate-limit page, also skipped.

### Tavora's own real site — `tavora_plan.png`, `tavora_trip_wizard.png`

Already referenced in `docs/internal/research-summary.md` §4 from earlier text
notes; these are the first actual screenshots. Most directly relevant
since it's literally the product we're extending.

- **Search/landing page**: one centered, pill-shaped "Where / When / Who"
  search bar (three fields in a single rounded container, not three
  separate boxes) sitting on plain white, with a promo banner strip above
  it and a result grid below, grouped by region with horizontal
  scroll-snap carousels per group. Cards: image, a small rounded status
  tag top-left ("Mountains this weekend"), a heart/save icon top-right,
  price + a black pill CTA button at the bottom.
- **Trip wizard page (the single most relevant reference)**: a colored
  (green) hero band holding trip context (destination, a back arrow, "Add a
  second place" chips) sits directly under the nav, with a compact white
  "trip facts" bar right below it (Dates / Duration / Travellers, each its
  own icon+label+value column, plus an "Edit trip" button on the right).
  Under that: a **numbered step tracker** (1 Travel — 2 Ride — 3 Stay — 4
  Extras — 5 Return — 6 Review) as circles connected by a line, the current
  step filled solid. The main content area is a filterable list of
  selectable option cards (icon, title, subtitle, a price/time on the
  right, a radio circle); filter pills (Direct only, rated 4+) and a sort
  dropdown sit above the list. A **sticky right-side summary card**
  ("SUMMARY — Your trip") mirrors the running selection and carries the
  single "Continue" call-to-action.
- **Direct takeaways for us**: our Request Form, Offer Review, and
  Dashboard are conceptually "step 1" / "step 3 (review)" / "the trips
  list" of exactly this same shape. The numbered step tracker and the
  sticky summary-card-with-CTA pattern are the two single most
  transferable ideas - they're exactly how a real user would expect a
  multi-step trip flow to look, and we currently have neither.

### Google Flights — `google_flights_search.png`

- A clean, minimal search card: a row of three dropdown-style controls
  (trip type / passenger count / class) above the origin/destination/date
  row; an explicit swap icon between origin and destination; one prominent
  pill-shaped primary action button, centered. Generous white space, a soft
  card shadow, no visual clutter competing with the form itself.
- **Takeaway**: a strong, low-risk reference for our Request Form
  specifically - our form today is a plain stacked list of labeled inputs;
  this shows the same fields can read as "a real travel product" just by
  grouping related controls into one bordered card and giving the submit
  action real visual weight.

### Booking.com — `booking_com_home.png`

- Dark hero banner with the search bar deliberately overlapping its bottom
  edge (half in the dark hero, half in the white content below) - a very
  common "hero search bar" pattern. A row of 4 icon+short-text trust/value
  columns directly under the fold ("book now pay later," "verified
  reviews," etc).
- **Takeaway**: lower priority for us than the other two references - this
  pattern fits a marketing landing page more than a logged-in utility
  dashboard, which is closer to what our Dashboard/Ops screens actually
  are. Worth keeping in mind only if we ever want a distinct "marketing/
  landing" moment before the mock-user switcher, which isn't currently
  planned.

### Not yet captured, worth a second pass later

- ixigo's actual Fare Alerts / Smart Lock screens specifically (not just
  its homepage) - the closest real competitor feature to our own
  monitor→alert→hold loop, per `docs/internal/research-summary.md` §6.2.2. Blocked
  this round by a generic rate-limit page, not a design judgment - retry
  before the UI pass starts if that specific reference still feels
  missing.
- Hopper's Price Freeze UI - mobile-app-first, not easily screenshot-able
  via a plain headless browser; would need a different approach (app store
  screenshots, review videos) if wanted later.

## Already fixed, not part of the pending UI pass

- The one real bug found live during this testing pass (a request with the
  return date on or before the outbound date silently produced priced-but-
  impossible results) is fixed and deployed - see `docs/internal/decision-log.md`'s
  "Request-input validation fix" entry and `backend/app/validation.py`.
  Mentioned here only so it isn't assumed to still be open.
- **Standing practice going forward**: any new UI work that adds or changes
  a user input gets its validation built at the same time, not after the
  fact - see memory note (if consulted in a future session) or just this
  line as the record of the decision.
