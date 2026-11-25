from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceObservation
from app.monitoring import run_check_and_alert
from app.ownership import get_owned_request
from app.schemas import PriceObservationOut

router = APIRouter(prefix="/api/requests", tags=["check"])


@router.get("/{request_id}/observations", response_model=list[PriceObservationOut])
def list_observations(
    request_id: int,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    # Read-only, no supplier calls - loading the dashboard shouldn't burn a Sabre/Hotelbeds quota call.
    # Paginated: a request checked every 5 minutes over a long-lived "watch" accumulates observations
    # without bound, unlike this app's other, naturally-small lists (users, requests, notifications).
    get_owned_request(request_id, user_id, db)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return (
        db.query(PriceObservation)
        .filter(PriceObservation.request_id == request_id)
        # id as a tiebreaker: two observations in the same cycle can share observed_at to the second
        .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/{request_id}/check", response_model=PriceObservationOut)
def check_price(request_id: int, user_id: int, db: Session = Depends(get_db)):
    trip_request = get_owned_request(request_id, user_id, db)
    if trip_request.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Request is {trip_request.status}, not active - resume it to check prices.",
        )
    # Date validation happens inside run_check_and_alert; manual button and scheduler share this same alert logic
    return run_check_and_alert(trip_request, db)
