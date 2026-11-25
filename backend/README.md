# Backend

FastAPI backend for the Trip Price Watch & Booking prototype.

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
3. Copy `.env.example` to `.env` and fill in real values - `DATABASE_URL`, plus
   your own Sabre and Hotelbeds test credentials (never commit `.env`; it's
   git-ignored at the repo root).
4. Seed the database - this also brings the schema up to date via real
   Alembic migrations (`backend/alembic/`), so there's no separate
   manual schema-creation step:
   ```
   python scripts/seed.py
   ```
   To run migrations on their own (no seed data), use `alembic upgrade head`
   directly.
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

## Running the tests

```
createdb tavora_test   # one-time, separate from the dev/prod database
pip install -r requirements-dev.txt
pytest
```

Tests run against `tavora_test`, not your dev database - each test starts
from a completely empty schema (see `tests/conftest.py`), so nothing here
touches or depends on your seeded dev data.

## What's real vs. simulated

- **Flights** - real Sabre Dev Studio sandbox call (Bargain Finder Max v4).
- **Hotels** - real Hotelbeds sandbox call (geolocation search), EUR to INR
  converted at a documented fixed rate (see `app/sources/hotels.py`).
- **Cabs** - simulated; no real fare source exists for this category, see
  `../docs/DATA_SOURCES.md` for the full reasoning.

Full reasoning for every architecture/source choice is in `../docs/METHODOLOGY_REPORT.md`.
