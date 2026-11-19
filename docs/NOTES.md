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

---

## 2026-11-19 — Repo + timeline + stack (see docs/DECISIONS.md for full reasoning)

- Private repo: `github.com/abhinavsingh-official/tavora-trip-watch`.
- Received Wed night 2026-11-18, demo Wed night 2026-11-25. Demo travel dates must be
  on/after 2026-12-25 (assignment's "30+ days after submission" rule).
- Backend: Python + FastAPI (settled). Frontend/DB/scheduler: still open.
- Confirmed with user: no AWS/cloud-provider infra for this project — the global
  CLAUDE.md infra-gate rules are scoped to company work, not this personal assignment.
