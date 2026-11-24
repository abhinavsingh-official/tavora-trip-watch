# Trip Price Watch — Plain-English Plan

*This is not the assignment. It's our own translation of it — same substance, no
exam-paper tone, organized by what actually matters instead of by document order.
The real brief lives in `docs/assignment.pdf`; the full research lives in
`docs/internal/research-summary.md` and `docs/internal/decision-log.md`. Read this one first.*

---

## 1. What we're actually building, in one breath

A tool where you tell it "I want to go from Mumbai to Goa, 2 people, 3 nights, under
₹35,000" — and instead of searching once, it **keeps checking** flight + hotel + cab
prices for you, and taps you on the shoulder the moment a real, complete price comes
in under your budget. You look at it, say yes, and it pretends to book it (clearly
labeled as pretend) — and it has to pretend *correctly*, meaning it doesn't double-book,
doesn't lie about what happened, and doesn't fall over if something goes wrong halfway.

That's it. Everything else in the brief is detail on how to make that one idea
trustworthy.

## 2. Where the points actually are

The grading weights are public, so there's no guessing needed about what matters:

| Area | Weight | What it really means |
|---|---|---|
| Booking correctness, concurrency, recovery | **30%** | Does the pretend-booking step behave like a real system would — no duplicates, no false "done" when something failed, no silent data loss |
| Source research & price data integrity | **20%** | Did we actually look for real data sources and are our numbers honest about being real vs. made-up |
| Monitoring & notification correctness | **20%** | Does the "keep checking and tell me when it's cheap enough" loop actually work right |
| Tests & reproducibility | **15%** | Can someone else run our tests and a load demo and get the same results |
| Methodology & live understanding | **10%** | Can we explain *why* we did it this way, out loud, without notes |
| Usability | **5%** | Does it look decent — explicitly the least important box to tick |

**The one sentence worth remembering under pressure:** more than half the grade (30%
booking + 20% monitoring) is about *one thing not breaking* — the request → price →
alert → booking pipeline behaving correctly and honestly. Everything else is in
service of that, or is cheap to pick up once that core thing exists.

## 3. Standing goals — these run the whole time, not just in one phase

Unlike the version plan below, these aren't things we finish and move past. They're
habits to keep up from day 1 to day 7:

- **Write down every real decision as we make it**, in plain language, in
  `docs/internal/decision-log.md` — not for the document's sake, but because the live interview
  explicitly tests whether you can explain and defend choices on the spot. If it's
  written down once in your own words, it's much easier to say out loud later.
- **Never let a gap be silent.** If something isn't built, or is stubbed, or is a
  shortcut — say so, in one line, near the thing itself. The brief explicitly says
  this is fine and even rewarded ("clearly explain incomplete work and its impact").
  A silent gap looks like a bug. A labeled gap looks like judgement.
- **Don't build more than the request asks.** No extra screens, no extra tech "to
  look serious." The brief explicitly says code volume and complexity don't earn
  credit by themselves — if anything, over-building makes the live review *harder*,
  because there's more surface area to be asked about and more to forget.
- **Keep the understanding, not just the code, up to date.** Before moving to the
  next version below, you (not Claude) should be able to say out loud, in your own
  words, what the current version does and why — if you can't, that's a sign to pause
  and talk it through rather than push forward.

## 4. A short glossary — the handful of ideas that show up everywhere

A few concepts keep recurring under different names across the brief. Once these
click, most of the rest reads as "the same idea, applied again":

- **Watcher, not search engine.** A normal travel site answers one question and
  forgets you. This tool remembers your request and keeps re-asking the question
  every few minutes, for as long as the request stays active.
- **Hold / lock.** Like ixigo's "Price Lock" or Hopper's "Price Freeze" — real
  products that let you pay a little to freeze a price for a short while. We're
  building a free, short (2-minute), simulated version of the same idea: once you've
  said "yes, book it," the price can't quietly change under you for those 2 minutes.
- **Freshness / staleness.** A price is only trustworthy for a little while. If it's
  too old, we shouldn't act on it as if it were current — we should say "this might be
  outdated" instead of pretending it's still true.
- **Complete vs. provisional vs. unavailable.** Not every price we fetch is a full,
  trustworthy number — sometimes a tax or fee is missing, sometimes a source just
  fails. Rather than guessing (or worse, treating "missing" as ₹0), we label the price
  honestly: whole and trustworthy, partially known, or just not available right now.
- **Idempotency** (the one genuinely unfamiliar word worth defining plainly): *doing
  the same action twice should not cause it to happen twice.* If a booking request
  gets sent, and then accidentally sent again (a retry, a glitch), the system should
  recognize "I already did this" and not create a second booking. This is the single
  idea behind most of the trickiest booking rules.
- **Concurrency.** What happens when two people try to grab the *same* last hotel
  room at the *same* moment. Only one of them should actually get it — the system has
  to pick a winner cleanly, not give it to both or neither.
- **Simulated vs. real/sandbox.** Some prices in this tool come from an actual
  company's free test system (real company, test data). Some are entirely made up by
  us, because no real/test source exists for that piece (e.g. cabs). Both are fine —
  the only rule is we're always honest on-screen about which is which.

## 5. The version plan — what "good enough" looks like at each stage

The brief itself admits a 7-day window with a full-time job is tight, and explicitly
says partial, honestly-labeled work is fine. So instead of one giant to-do list, this
is four stacked versions — each one a complete, demoable thing on its own, each one
making the previous version more correct or more complete rather than adding
unrelated new features. If time runs out at the end of any version, that version is
still a respectable, honest thing to show and talk about.

### V1 — "It works once, start to finish" (the skeleton)

**Goal:** prove the entire idea can happen for one request, by hand, even if nothing
runs automatically yet.

- One mock user, one request (pick User A — Mumbai/Goa, simplest numbers).
- A page to create that request.
- A "check price now" button that fetches/simulates a flight + hotel + cab price and
  adds them into one itemized total.
- If that total is under budget, show one in-app notification.
- A review screen where you see the (re-checked) price again and click "book."
- Booking pretends to book all three pieces and shows a result — even if, at this
  stage, it only handles the happy path (nothing's deliberately broken yet).

**Explicitly NOT in V1, and that's fine:** the other two mock users, the automatic
5-minute timer, price history, the re-alert/reset rules, holds actually expiring,
any of the six failure scenarios, tests, load demo. All of that is V2+.

**Why this order:** this is the one path the live interview will almost certainly ask
you to trace end to end. Getting it working and *understood* once, completely, is
worth more than having five unfinished pieces of a bigger system.

### V2 — "The core loop is actually correct and safe" (depth, not breadth)

**Goal:** take the one path from V1 and make it behave the way a real system has to
— this is where most of the 30%+20% grading weight actually lives.

- Turn "check price now" into a real recurring timer (every 5 minutes) plus keep the
  manual button.
- Store every single check as its own record — never overwrite, never erase, even
  when a check fails.
- Add the real alert rules: alert the first time it's under budget; only alert again
  if the price drops at least 5% further; going back over budget resets that; a
  failed check does nothing either way.
- Make the 2-minute hold real: re-check the price when the offer screen opens, make
  the user explicitly say yes again, and freeze the held price until it expires.
- Pick **one** of the six booking failure scenarios from the brief — most likely
  "one piece books, then another piece fails" — and make it behave correctly
  end-to-end (cancel the piece that succeeded, show a clear partial status). This one
  scenario, done properly, demonstrates you understand the whole failure-handling
  idea, which generalizes to the rest even if they're not all individually built yet.

**Explicitly deferred, and why that's an honest trade, not a cop-out:** the other five
failure scenarios follow the *same pattern* as the one above — once one is genuinely
done and understood, the others are mostly "more of the same shape," and that's
exactly the kind of thing worth saying plainly in the write-up rather than rebuilding
five times under time pressure.

### V3 — "It covers what it's supposed to cover" (breadth)

**Goal:** now that the core is correct for one case, stretch it to actually match the
brief's required scope — this is where "touched every part" becomes true.

- Add the other two mock users (B and D needs testing differently from A/C since it's
  the 4-adult/2-room case — that's the one that actually exercises occupancy math).
- Add edit / pause / cancel for a request, including: editing a request invalidates
  whatever offer was sitting around for the old version of it.
- Add a basic automated test for each of the things most likely to silently break:
  the price-adding-up math, the alert on/off rules, and "user A can't see user B's
  stuff."
- Add the small "operations" screen that shows anything stuck in a weird state (e.g.
  the partial-failure case from V2) so it's not invisible.

**Explicitly deferred:** the full scenario-replay tooling and the 100-request load
test — those are V4, since they're about *proving* things at scale, which only makes
sense once there's a real breadth of behavior worth proving.

### V4 — "Prove it, stress it, polish it" (stretch goals, do these only if time allows)

**Goal:** the parts of the brief that are real, graded, and worth doing — but are
explicitly the ones to sacrifice first if the week runs out, because they prove
things we can also just *explain* credibly in the live review if they're not built.

- The "fast-forward time / force a price / force a failure" controls so the scenarios
  can be demoed on command instead of waiting for real time to pass.
- The remaining failure scenarios, if time allows, using the same pattern from V2.
- The 100-request load demo and its report.
- Visual polish — explicitly last, per the brief's own 5% weighting.

*(Updated 2026-11-21: Hotelbeds registration and real test calls — originally
planned for V4 above — happened far earlier than expected, in the research phase
before any code was written. Flights (Sabre) and hotels (Hotelbeds) are both
confirmed real sandbox sources wired into V1 itself, not deferred. See
`docs/internal/research-summary.md` and `docs/versions/V1.md` for the actual state.)*

## 6. Signal vs. noise — reading the earlier AI-written breakdown with a human eye

The section-by-section breakdown we did earlier (still accurate, still useful as a
reference) was written by an AI reading a written brief very literally, without the
benefit of knowing how a real interview conversation actually goes. A few corrections
worth keeping in mind so it doesn't turn into exam-style over-preparation:

- **The brief's exact numbers (5 minutes, 2 minutes, 5%, 100 requests) matter far less
  than understanding *why* a number like that exists at all.** If you can explain "we
  re-check periodically because prices move, and we only re-alert on a real further
  drop so we don't spam the user with noise," you've answered the spirit of it — the
  interviewer is very unlikely to grill you on whether it's exactly 5% vs 7%.
- **The six-row failure table reads as six separate things to build. In practice it's
  one idea (don't lie about what happened; don't do the same thing twice) applied six
  times.** Build and deeply understand one of them (V2 above); be able to *talk
  through* the other five in plain language without necessarily having coded them.
- **The "deliverables" list (Methodology Report, How-it-works Guide, Data-source
  Dossier, etc.) sounds like five separate heavy documents. It's really one small set
  of facts, written up three or four different ways.** Nearly everything in all of
  them is already captured once in `DECISIONS.md` and `research_summary.md` — the
  "deliverables" are mostly a formatting/assembly pass at the end, not new work.
- **A real interview is a conversation, not a court case.** The live-review section
  explicitly allows AI help and only asks that *you* can explain and verify it. That
  means the honest, comfortable answer to almost any question is some version of: "I
  built X, here's why, here's what I'd do with more time, and here's the one part I
  didn't get to and why I made that call" — not reciting a memorized justification for
  every single number in the brief.
- **It's explicitly fair, and said out loud in the brief itself, that one week with a
  full-time job won't finish this completely.** The grading rewards *honest, clear
  explanation of what's incomplete* as much as it rewards finished work. Don't treat
  an unfinished V4 as a failure — treat a well-understood, well-explained V1-V3 as a
  genuinely strong submission.

## 7. A few one-liners for the live conversation, plain-language versions

Worth having these ready in your own words, not memorized verbatim:

- *"Why does this watch prices instead of just searching?"* — Because the brief's own
  framing is about tracking a trip over time against a budget, not a one-time search
  — that's the one structural idea the whole system is built around.
- *"Why don't you have real flight/hotel/cab APIs for everything?"* — Because in
  India, for a 7-day window with no paid subscriptions, that data mostly isn't
  reachable for free — we checked, repeatedly, and documented exactly what's real
  (flights), what's a real free test system with fake prices (also flights, and maybe
  hotels), and what's an honest simulation built on real-world reference numbers
  (cabs, using regulatory fare caps and real distance data).
- *"How do you stop a double booking?"* — By checking "did I already do this?" before
  acting, instead of just trying again blindly — the same idea behind not double-
  charging a card if a payment request gets sent twice by accident.
- *"What happens if something fails halfway through booking?"* — We try to undo the
  part that succeeded, and if even that fails, we don't pretend it's fixed — we flag
  it clearly as needing a person to look at it.
- *"What would you do with another week?"* — Have this answer ready honestly, from
  whichever version you actually reached — it's a real, expected question, not a trap.

---

*This document is the plain-language companion to the real assignment
(`docs/assignment.pdf`), the full research (`docs/internal/research-summary.md`), and the
formal decision log (`docs/internal/decision-log.md`). Use this one to think and talk about the
project; use those for the precise wording and evidence when it's needed.*
