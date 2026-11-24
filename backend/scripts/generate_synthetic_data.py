"""
Generates the synthetic flight and cab directories that the live product
actually reads from (see app/models.py's SyntheticFlightOption /
SyntheticCabOption docstrings for why - Sabre's real sandbox fares never
move call to call, and no real cab-fare source exists at all).

Deterministic and idempotent: re-running clears and regenerates, same seed
-> same output, so this is replayable per Sec. 11's own requirement, not a
one-off hand-edit. Run once (or after a fare-baseline change):
  .venv/bin/python scripts/generate_synthetic_data.py
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import SyntheticCabOption, SyntheticFlightOption

"""
Real India domestic carriers actually operating these routes - used for
realism, not as a claim that this specific flight/price/time is real
(it isn't; it's clearly labeled synthetic everywhere it's shown).
"""
CARRIERS = [
    ("6E", "IndiGo"),
    ("AI", "Air India"),
    ("UK", "Vistara"),
    ("SG", "SpiceJet"),
    ("I5", "AirAsia India"),
    ("QP", "Akasa Air"),
]

"""
One real round-trip leg per demo user (origin, destination, travel date),
from scripts/seed.py's Sec. 02 values - this is what's actually generated;
an edited request with a different route/date falls back to a live Sabre
call (same fallback pattern as hotels.py).

base_price_inr is PER ADULT, not per booking - a real Sabre fare search is
priced per passenger (the live path calls it with trip_request.adults),
so flights.py multiplies current_price_inr by the real adult count at
read time rather than storing one flat group total. Anchored to the one
real Sabre observation this project captured (BOM->GOI, 2 adults,
~INR 7492 total -> ~3750/adult); the other routes are estimated from that
same per-adult order of magnitude, scaled for approximate distance.
"""
ROUTES = [
    {"label": "User A outbound", "origin": "BOM", "destination": "GOI", "travel_date": date(2026, 12, 26), "base_price_inr": 3700.0},
    {"label": "User A return", "origin": "GOI", "destination": "BOM", "travel_date": date(2026, 12, 29), "base_price_inr": 3550.0},
    {"label": "User B outbound", "origin": "DEL", "destination": "GOI", "travel_date": date(2026, 12, 26), "base_price_inr": 4750.0},
    {"label": "User B return", "origin": "GOI", "destination": "DEL", "travel_date": date(2026, 12, 29), "base_price_inr": 4600.0},
    {"label": "User C outbound", "origin": "BOM", "destination": "JAI", "travel_date": date(2026, 12, 26), "base_price_inr": 3250.0},
    {"label": "User C return", "origin": "JAI", "destination": "BOM", "travel_date": date(2026, 12, 28), "base_price_inr": 3150.0},
]

OPTIONS_PER_ROUTE = 10


def _generate_time(rng: random.Random) -> tuple[str, str]:
    departure_hour = rng.randint(5, 21)
    departure_minute = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    duration_minutes = rng.randint(80, 150)
    total_minutes = departure_hour * 60 + departure_minute + duration_minutes
    arrival_hour = (total_minutes // 60) % 24
    arrival_minute = total_minutes % 60
    return (
        f"{departure_hour:02d}:{departure_minute:02d}",
        f"{arrival_hour:02d}:{arrival_minute:02d}",
    )


def generate_and_store():
    db = SessionLocal()
    try:
        total = 0
        for route in ROUTES:
            db.query(SyntheticFlightOption).filter(
                SyntheticFlightOption.origin_code == route["origin"],
                SyntheticFlightOption.destination_code == route["destination"],
                SyntheticFlightOption.travel_date == route["travel_date"],
            ).delete()

            """Seeded by route+date, not by wall-clock time - same route
            always generates the same directory, so this is genuinely
            replayable (Sec. 11), not random noise per run."""
            rng = random.Random(f"{route['origin']}-{route['destination']}-{route['travel_date']}")

            for i in range(OPTIONS_PER_ROUTE):
                carrier_code, carrier_name = rng.choice(CARRIERS)
                flight_number = rng.randint(100, 999)
                departure_time, arrival_time = _generate_time(rng)
                stops = 0 if rng.random() < 0.75 else 1
                price_variance = rng.uniform(-0.18, 0.22)
                price = round(route["base_price_inr"] * (1 + price_variance), 2)

                db.add(
                    SyntheticFlightOption(
                        origin_code=route["origin"],
                        destination_code=route["destination"],
                        travel_date=route["travel_date"],
                        carrier_code=carrier_code,
                        carrier_name=carrier_name,
                        flight_number=flight_number,
                        departure_time=departure_time,
                        arrival_time=arrival_time,
                        stops=stops,
                        base_price_inr=price,
                        current_price_inr=price,
                    )
                )
                total += 1
            print(f"{route['label']}: {OPTIONS_PER_ROUTE} synthetic flight options generated.")

        db.commit()
        print(f"Done. {total} synthetic flight options stored.")

        """
        Cab directory: real anchors from cabs.py's own documented RTO rate
        cards / tempo-traveller market range - just expanded into a
        browsable set of vehicle classes instead of one flat formula.
        """
        db.query(SyntheticCabOption).delete()
        """
        The Tempo Traveller price (30km assumed leg distance x real
        ₹24/km tempo-traveller market rate) is cabs.py's own existing
        anchor, not a new guess - the other three are priced around it.
        """
        cab_options = [
            {"vendor_name": "CityLink Transfers", "vehicle_class": "Sedan", "passenger_capacity": 4, "luggage_capacity": 2, "base_price_per_leg_inr": 900.0},
            {"vendor_name": "Metro Comfort Cabs", "vehicle_class": "Sedan", "passenger_capacity": 4, "luggage_capacity": 3, "base_price_per_leg_inr": 1050.0},
            {"vendor_name": "Highway SUV Rentals", "vehicle_class": "SUV", "passenger_capacity": 6, "luggage_capacity": 5, "base_price_per_leg_inr": 1600.0},
            {"vendor_name": "Horizon Tempo Services", "vehicle_class": "Tempo Traveller", "passenger_capacity": 12, "luggage_capacity": 8, "base_price_per_leg_inr": 30 * 24.0},
        ]
        for option in cab_options:
            price = round(option["base_price_per_leg_inr"], 2)
            db.add(
                SyntheticCabOption(
                    vendor_name=option["vendor_name"],
                    vehicle_class=option["vehicle_class"],
                    passenger_capacity=option["passenger_capacity"],
                    luggage_capacity=option["luggage_capacity"],
                    base_price_per_leg_inr=price,
                    current_price_per_leg_inr=price,
                )
            )
        db.commit()
        print(f"Done. {len(cab_options)} synthetic cab vehicle classes stored.")
    finally:
        db.close()


if __name__ == "__main__":
    generate_and_store()
