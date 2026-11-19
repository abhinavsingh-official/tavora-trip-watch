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

## 2026-11-19 — Repo + timeline + stack (see docs/DECISIONS.md for full reasoning)

- Private repo: `github.com/abhinavsingh-official/tavora-trip-watch`.
- Received Wed night 2026-11-18, demo Wed night 2026-11-25. Demo travel dates must be
  on/after 2026-12-25 (assignment's "30+ days after submission" rule).
- Backend: Python + FastAPI (settled). Frontend/DB/scheduler: still open.
- Confirmed with user: no AWS/cloud-provider infra for this project — the global
  CLAUDE.md infra-gate rules are scoped to company work, not this personal assignment.
