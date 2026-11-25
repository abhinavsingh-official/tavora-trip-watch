# Known Issues & What's Needed for Production

Plain-language version: what's not quite right today, and what would need to change before this
could be a real product people pay for - written so the "why" makes sense even if you don't know
the tech by name.

## Known issues

**"Provisional" status is never actually used.** The database has a slot for a price check that
comes back half-finished (some prices known, some missing) - a status called `provisional`. In
practice, every real check we run comes back either fully complete or fully failed, never half-done,
so this status exists in the code but has never actually fired. Not a bug, just unused.

**The cache and rate-limiter only remember things for one running copy of the app.** We keep a
short-term memory ("cache") so we don't hammer Hotelbeds with repeat calls, and a counter that stops
us from calling it too often ("rate limiter"). Both live in the memory of whichever single copy of
the backend is currently running. That's fine today, because there's only one copy running. If we
ever ran several copies at once to handle more traffic, each copy would have its own separate memory
instead of sharing one - so two copies could accidentally go over the shared quota together without
either one noticing. Not a problem at this project's scale, but worth knowing about.

**Euro-to-Rupee conversion uses one fixed number, not a live exchange rate.** Hotelbeds (our hotel
data source) gives prices in Euros. We convert to Rupees using one fixed rate written into the code,
not a live, constantly-updating rate like a bank would use. If the real exchange rate moves, our
numbers don't follow it.

**The free hosting plan sleeps after 15 minutes of no traffic.** We're hosting on Render's free
tier. If nobody visits for 15 minutes, the backend shuts itself down to save resources, and the next
visitor waits 30-60 seconds for it to wake back up. This is a hosting limitation, not a code defect.

**Visual polish was deliberately left for last.** We prioritized correctness (right prices, no
duplicate bookings, proper failure handling) over making every screen look finished, since the
assignment itself says that's what should matter most.

**One shared 2-minute hold instead of three separate ones.** When you review a price, we freeze
("hold") that price for 2 minutes so it can't quietly change on you. The spec technically wanted the
flight, the hotel, and the cab to each have their *own* 2-minute timer. We built one single timer for
the whole trip instead - since all three are priced at the exact same moment anyway, there's no
practical difference today, but it's a simplification worth knowing about rather than a hidden gap.

**Fast-forwarding time in Simulation affects the whole app, not just the test sandbox.** The
Simulation page lets you skip time forward, which is useful for testing things like "what happens
when a hold expires." Right now, doing that shifts the clock for *everyone* - including the real
demo users A, B, and C - not just the simulated test user. It should be scoped to the sandbox only;
right now it isn't.

A full review of the whole app also found and fixed 11 separate real bugs along the way - most
notably a cancelled trip that could somehow still be booked, and a test tool (the Simulation price
override) that didn't behave the same way twice. All 11 are fixed and have tests guarding against
them coming back.

## What would be needed for production

**Real deals with the price suppliers.** Flights and hotels right now come from real *test/sandbox*
accounts (Sabre, Hotelbeds) - realistic, but not actual bookable live prices. Cabs are entirely made
up (simulated), because no cab company would give us real API access inside a one-week project. A
real product would need actual paid/business agreements with suppliers like these, plus a real cab
company (Ola's or CabBazar's outstation-transfer APIs are the closest real fit found, but both require
a business partnership to access).

**A background job system that can run across multiple machines.** Right now, one single background
process checks every trip's price every 5 minutes, one at a time ("APScheduler" - a simple built-in
scheduler that lives inside our one app process). That's fine for a handful of trips. With thousands
of real users, that one process would become a bottleneck - you'd want to spread that checking work
across several machines working together. A common way to do that is a tool called **Celery** paired
with **Redis** (a fast, shared memory store that multiple machines can all read from at once), instead
of relying on one process's own private memory.

**Shared memory instead of each copy keeping its own.** Directly related to the point above: the
cache and rate-limiter mentioned in "Known issues" would need to move into that same shared Redis
store, so multiple running copies of the app coordinate instead of each guessing independently.

**Real logins, not a dropdown.** Right now you just pick which demo person you are (User A, B, or C)
from a dropdown - there's no password, no real account. A real product needs actual user accounts
and authentication.

**A live currency exchange rate**, replacing the one fixed Euro-to-Rupee number, so hotel prices stay
accurate as the real rate moves.

**Per-component holds**, if a real deployment ever needed the flight, hotel, and cab to expire at
different times (e.g. because one supplier's real quote is only valid for 1 minute and another's for
5). Today's single shared hold assumes they're all equally fresh, which has been true in every case
tested here.

**Visual polish** - the one item we knowingly left for last, on purpose, since it's worth the least
toward getting the core logic right.
