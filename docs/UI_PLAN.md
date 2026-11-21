# UI / Polish Plan — working notes

*Living document for the UI pass that comes after V4. Unlike `docs/versions/
*.md`, this isn't a record of something shipped — it's where the plan lives
while it's still being decided, so a conversation doesn't become the only
place it's written down. Once this pass actually ships, its real content
moves into a new `docs/versions/V5.md` (or whichever version number it
ends up being), same as every prior version.*

## Status (as of 2026-11-22, night)

**No UI implementation has started.** By explicit instruction, nothing
further gets built until the candidate has gone through the live
deployment and every doc themselves (expected to take through tomorrow or
Monday night) and comes back with a batched list of specific UI changes.
When that list arrives, it replaces/extends this document - it is not
starting from a blank slate, but it is also not something to second-guess
or re-litigate once given.

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

- **Scenario Lab wording is "worded weirdly"** (candidate's words) - needs
  an actual copy pass once the real pages are polished, not just a
  find-and-replace. Not yet scoped in detail - do that once the batched
  list arrives and it's clear how much of the Lab's framing needs to change
  to match the rest of the product's new look.
- Whatever else the candidate's own stress-testing and doc review surfaces
  - this section is a placeholder until that list exists.

## Already fixed, not part of the pending UI pass

- The one real bug found live during this testing pass (a request with the
  return date on or before the outbound date silently produced priced-but-
  impossible results) is fixed and deployed - see `docs/DECISIONS.md`'s
  "Request-input validation fix" entry and `backend/app/validation.py`.
  Mentioned here only so it isn't assumed to still be open.
- **Standing practice going forward**: any new UI work that adds or changes
  a user input gets its validation built at the same time, not after the
  fact - see memory note (if consulted in a future session) or just this
  line as the record of the decision.
