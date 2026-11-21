# Backend — V1

FastAPI backend for the Trip Price Watch & Booking prototype. See
`docs/versions/V1.md` and `docs/versions/V1_MODULES.md` for what this version
does and the full module-by-module build spec.

## Setup

1. Install Postgres locally (or point `DATABASE_URL` at any reachable instance)
   and create an empty database, e.g.:
   ```
   createdb tavora
   ```
2. Create a virtualenv and install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in real values — `DATABASE_URL`, plus
   your own Sabre and Hotelbeds test credentials (never commit `.env`; it's
   git-ignored at the repo root).
4. Seed the database:
   ```
   python scripts/seed.py
   ```
5. Start the server:
   ```
   uvicorn app.main:app --reload
   ```
   The API is then at `http://localhost:8000`, interactive docs at
   `http://localhost:8000/docs`.

To wipe everything and reseed from scratch:
```
python scripts/reset.py
```

## What's real vs. simulated in V1

- **Flights** — real Sabre Dev Studio sandbox call (Bargain Finder Max v4).
- **Hotels** — real Hotelbeds sandbox call (geolocation search), EUR→INR
  converted at a documented fixed rate (see `app/sources/hotels.py`).
- **Cabs** — simulated; no real fare-source exists for this category (see
  `docs/research_summary.md` Sec. 6.4/7.3).

Full reasoning for every choice above is in `docs/DECISIONS.md`.
