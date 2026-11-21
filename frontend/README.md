# Frontend — V1

React + Vite + TypeScript frontend for the Trip Price Watch & Booking prototype.
See `docs/versions/V1.md` and `docs/versions/V1_MODULES.md` for what this
version does and the full module-by-module build spec.

## Setup

```
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api/*` to the
backend at `http://localhost:8000` (see `vite.config.ts`) — start the backend
first (see `../backend/README.md`).

## Pages

- `/` — Dashboard: lists the current mock user's requests, "Check price now"
- `/new` — create a new trip request
- `/notifications` — lists alerts; opening one re-checks the price fresh
- `/offer/:notificationId` — the revalidated offer, "Confirm booking (simulated)"
- `/booking/:bookingId` — the booking result, per-component status + fake refs
- `/lab` — Scenario Lab: simulated clock + price overrides, dev/demo-only
