# Tavora Trip Price Watch & Booking

Take-home product developer assignment for Tavora. See `docs/assignment.pdf` for the
original brief and `docs/DECISIONS.md` for the running methodology/decision log built
up while working through it section by section.

Status: V2 built and verified end to end - real automatic monitoring,
real alert rules, real 2-minute holds, and one real booking-failure scenario
with compensation (see `docs/versions/V2.md`).

**Live demo**: https://tavora-frontend-2ldl.onrender.com (backend:
https://tavora-backend-fm0b.onrender.com) - deployed on Render, free tier.
Note the free backend spins down after 15 minutes idle; the first request
after that takes ~30-60s to wake it up.
