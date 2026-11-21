# Tavora Trip Price Watch & Booking

Take-home product developer assignment for Tavora. See `docs/assignment.pdf` for the
original brief and `docs/DECISIONS.md` for the running methodology/decision log built
up while working through it section by section.

Status: V4 built and verified end to end - all six Sec. 09 booking
failure-table rows (idempotent retries, inventory-disappears/hold-expiry,
partial-failure compensation, supplier-timeout reconciliation,
restart-resume, cancellation-failure/manual-intervention), all seven Sec. 11
scenarios replayable via the Scenario Lab, a 27-test automated suite, and a
real 100-request/3-cycle load demonstration (see `docs/versions/V4.md`). All
five Sec. 14 deliverable documents are in `docs/`.

**Live demo**: https://tavora-frontend-2ldl.onrender.com (backend:
https://tavora-backend-fm0b.onrender.com) - deployed on Render, free tier.
Note the free backend spins down after 15 minutes idle; the first request
after that takes ~30-60s to wake it up.
