# Tavora Trip Price Watch & Booking

![CI](https://github.com/abhinavsingh-official/tavora-trip-watch/actions/workflows/ci.yml/badge.svg)

Take-home product developer assignment for Tavora. See `docs/assignment.pdf` for the
original brief and `docs/internal/decision-log.md` for the running methodology/decision log built
up while working through it section by section.

Status: V4 built and verified end to end - all six Sec. 09 booking
failure-table rows (idempotent retries, inventory-disappears/hold-expiry,
partial-failure compensation, supplier-timeout reconciliation,
restart-resume, cancellation-failure/manual-intervention), all seven Sec. 11
scenarios replayable via the Scenario Lab, a 32-test automated suite
(including a request-input validation fix found by live testing after V4 -
see `docs/internal/decision-log.md`), and a real 100-request/3-cycle load demonstration
(see `docs/versions/V4.md`). All five Sec. 14 deliverable documents are in
`docs/`.

V5 adds a real design system and a restructured Request Form/Offer Review
(grouped sections, sticky summary-card-with-CTA, borrowed from a real
frontend reference survey - see `docs/internal/ui-plan.md`) and a full Scenario Lab
copy rewrite. See `docs/versions/V5.md` for the full record.

V6 adds a real homepage, a per-request "trip story" view showing the real
alternative flights/hotels a check actually found (the one used visibly
marked "Picked" - zero new supplier calls, it reads data already stored),
and a warm accent color in place of black/white. See `docs/versions/V6.md`.

V7 fixes all 11 findings from a full audit (`docs/internal/audit-log-2026-11-23.md`) -
most notably, a cancelled/paused request could still be reviewed and fully
booked, and a Scenario Lab price override wasn't actually deterministic -
adds real Alembic schema migrations (`backend/alembic/`, a previously
missing Sec. 14 item), sets up CI (`.github/workflows/ci.yml`: backend
tests + a fresh-database migration check, frontend build), and closes a
further gap found during a fresh requirements re-read: Sec. 06's "lowest
observed valid total" and price-history chart were never actually built
despite being marked done - now a real part of the Dashboard. 47 tests
passing. See `docs/versions/V7.md`.

**Live demo**: https://tavora-frontend-2ldl.onrender.com (backend:
https://tavora-backend-fm0b.onrender.com) - deployed on Render, free tier.
Note the free backend spins down after 15 minutes idle; the first request
after that takes ~30-60s to wake it up.
