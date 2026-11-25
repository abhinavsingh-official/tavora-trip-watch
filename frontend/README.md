# Frontend

React + Vite + TypeScript frontend for the Trip Price Watch & Booking prototype.

## Setup

```
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api/*` to the
backend at `http://localhost:8000` (see `vite.config.ts`) - start the backend
first (see `../backend/README.md`).

## Pages

- `/` - Home: plain landing page, not the user's own data
- `/dashboard` - every request, current totals, price-history chart, "Check price now"
- `/new` (and `/requests/:id/edit`) - create or edit a trip request
- `/requests/:id/story` - "Your Bookings": itemized total, pay a held offer or buy now, browse the real candidates
- `/offer/:notificationId` - revalidated offer review, 2-minute hold countdown, "Confirm booking (simulated)"
- `/booking/:bookingId` - booking result, per-component status + simulated supplier refs
- `/lab` - Simulation: deterministic fixtures for every required demo scenario, dev/demo only

Notifications live in the header bell's dropdown, not a separate page; the operations view for
unresolved partial bookings is the Dashboard's "Needs attention" card.
