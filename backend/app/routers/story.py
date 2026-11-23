"""The "trip story" view (requested directly: show the real alternative
flights/hotels, with the one actually used highlighted, so the product
reads as a travel site making a visible choice - not just a calculator).

Read-only, additive, and ownership-scoped like every other real screen.
Never calls a real supplier itself - it only re-reads the raw response
already stored on the latest check (app/story.py), so looking at this page
repeatedly costs zero extra Hotelbeds/Sabre quota.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceObservation
from app.ownership import get_owned_request
from app.schemas import TripStoryOut
from app.story import extract_flight_candidates, extract_hotel_candidates

router = APIRouter(prefix="/api/requests", tags=["story"])


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
    hotel_candidates = extract_hotel_candidates(hotel_raw, trip_request.min_star_rating)

    def _mark_selected(candidates: list[dict], actual_price) -> list[dict]:
        # The "selected" one is whichever candidate's price matches the
        # price actually stored on this observation - not just "the
        # cheapest in this list again", since pricing.py's own eligibility
        # filtering already produced that stored price; this just finds it.
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
