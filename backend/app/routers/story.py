"""Trip story view - shows alternatives alongside the picked option, re-reading the stored raw response
(app/story.py) so it never burns extra supplier quota."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceObservation
from app.ownership import get_owned_request
from app.schemas import TripDirectoryOut, TripStoryOut
from app.sources import cabs, flights, hotels
from app.story import extract_flight_candidates, extract_hotel_candidates

router = APIRouter(prefix="/api/requests", tags=["story"])


@router.get("/{request_id}/directory", response_model=TripDirectoryOut)
def get_trip_directory(request_id: int, user_id: int, db: Session = Depends(get_db)):
    # "Your Bookings" reads this (always-live candidate tables); /story below is a snapshot of one past check instead
    trip_request = get_owned_request(request_id, user_id, db)

    flight_candidates = flights.get_flight_candidates(trip_request, db)
    hotel_candidates = hotels.get_hotel_candidates(trip_request, db)
    cab_candidates = cabs.get_cab_candidates(trip_request, db)

    def _mark_cheapest_selected(candidates: list[dict]) -> list[dict]:
        """Each list is already sorted cheapest-first; the first one is exactly what pricing.py would pick."""
        return [{**c, "selected": i == 0} for i, c in enumerate(candidates)]

    return TripDirectoryOut(
        outbound_flight_candidates=_mark_cheapest_selected(flight_candidates["outbound"]),
        return_flight_candidates=_mark_cheapest_selected(flight_candidates["return"]),
        hotel_candidates=_mark_cheapest_selected(hotel_candidates),
        cab_candidates=_mark_cheapest_selected(cab_candidates),
    )


@router.get("/{request_id}/story", response_model=TripStoryOut)
def get_trip_story(request_id: int, user_id: int, db: Session = Depends(get_db)):
    trip_request = get_owned_request(request_id, user_id, db)

    observation = (
        db.query(PriceObservation)
        .filter(PriceObservation.request_id == request_id)
        .order_by(PriceObservation.observed_at.desc())
        .first()
    )
    if observation is None:
        raise HTTPException(
            status_code=404,
            detail="No price check yet for this request - run 'Check price now' first.",
        )

    raw = observation.raw_sources or {}
    flight_raw = raw.get("flight") or {}
    hotel_raw = raw.get("hotel")

    outbound_candidates = extract_flight_candidates(flight_raw.get("outbound"))
    return_candidates = extract_flight_candidates(flight_raw.get("return"))
    # Use the filter in effect when this check ran, not the current value, so a later edit can't disappear the pick
    min_star_rating = (
        observation.min_star_rating_used
        if observation.min_star_rating_used is not None
        else trip_request.min_star_rating
    )
    hotel_candidates = extract_hotel_candidates(hotel_raw, min_star_rating)

    def _mark_selected(candidates: list[dict], actual_price) -> list[dict]:
        """Match on the price stored on the observation, not "cheapest in this list" (pricing.py already filtered)."""
        if actual_price is None:
            return [{**c, "selected": False} for c in candidates]
        target = float(actual_price)
        marked = False
        out = []
        for c in candidates:
            is_match = not marked and abs(c["price_inr"] - target) < 0.01
            if is_match:
                marked = True
            out.append({**c, "selected": is_match})
        return out

    return TripStoryOut(
        observation_id=observation.id,
        observed_at=observation.observed_at,
        outbound_flight_candidates=_mark_selected(
            outbound_candidates, observation.flight_outbound_price
        ),
        return_flight_candidates=_mark_selected(
            return_candidates, observation.flight_return_price
        ),
        hotel_candidates=_mark_selected(hotel_candidates, observation.hotel_total_price),
        cab={
            "outbound_price": observation.cab_outbound_price,
            "return_price": observation.cab_return_price,
            "status": observation.cab_status,
        },
    )
