"""
Generates the synthetic flight and cab directories the live product reads
from (Sabre's sandbox fares never change, and there's no real cab-fare
source at all - see SyntheticFlightOption/SyntheticCabOption in models.py).

Deterministic: same seed always produces the same output, so re-running
just clears and regenerates rather than hand-editing. Run once, or after
changing a fare baseline:
  .venv/bin/python scripts/generate_synthetic_data.py
"""

import random
import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import SyntheticCabOption, SyntheticFlightOption

"""
Real Indian domestic carriers, used for realism - the actual flights/prices
generated are still synthetic and labeled as such everywhere they're shown.
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
One round-trip leg per demo user, matching scripts/seed.py's requests. An
edited request with a different route/date falls back to a live Sabre call,
same as hotels.py does.

base_price_inr is PER ADULT, not per booking - Sabre prices per passenger,
so flights.py multiplies by adult count at read time instead of storing a
flat group total. BOM->GOI is anchored to a real Sabre fare we captured
(~3750/adult); the rest are estimated at the same order of magnitude,
scaled roughly for distance.
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

            # Seeded by route+date, not wall-clock time, so the same route
            # always generates the same directory instead of random noise.
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

        # Cab directory: every class assumes the same representative
        # one-way airport-to-hotel transfer distance, priced off a real
        # per-km market rate for its vehicle class - not a flat guess, and
        # not pretending to know the actual distance for every city pair.
        db.query(SyntheticCabOption).delete()
        TRANSFER_DISTANCE_KM = 30.0
        cab_options = [
            {"vendor_name": "CityLink Transfers", "vehicle_class": "Sedan", "passenger_capacity": 4, "luggage_capacity": 2, "per_km_rate_inr": 14.0},
            {"vendor_name": "Metro Comfort Cabs", "vehicle_class": "Sedan", "passenger_capacity": 4, "luggage_capacity": 3, "per_km_rate_inr": 16.0},
            {"vendor_name": "Highway SUV Rentals", "vehicle_class": "SUV", "passenger_capacity": 6, "luggage_capacity": 5, "per_km_rate_inr": 20.0},
            {"vendor_name": "Horizon Tempo Services", "vehicle_class": "Tempo Traveller", "passenger_capacity": 12, "luggage_capacity": 8, "per_km_rate_inr": 24.0},
        ]
        for option in cab_options:
            price = round(TRANSFER_DISTANCE_KM * option["per_km_rate_inr"], 2)
            db.add(
                SyntheticCabOption(
                    vendor_name=option["vendor_name"],
                    vehicle_class=option["vehicle_class"],
                    passenger_capacity=option["passenger_capacity"],
                    luggage_capacity=option["luggage_capacity"],
                    distance_km=TRANSFER_DISTANCE_KM,
                    per_km_rate_inr=option["per_km_rate_inr"],
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
