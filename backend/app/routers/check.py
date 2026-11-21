from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceObservation
from app.monitoring import run_check_and_alert
from app.ownership import get_owned_request
from app.schemas import PriceObservationOut

router = APIRouter(prefix="/api/requests", tags=["check"])


@router.get("/{request_id}/observations", response_model=list[PriceObservationOut])
def list_observations(request_id: int, user_id: int, db: Session = Depends(get_db)):
    # Read-only - does NOT call any real supplier. Exists so the Dashboard can
    # show the latest known price without triggering a brand-new (quota-
    # costing) Sabre/Hotelbeds call just from loading the page; "check price
    # now" is the only thing that should ever call build_package.
    get_owned_request(request_id, user_id, db)
    return (
        db.query(PriceObservation)
        .filter(PriceObservation.request_id == request_id)
        .order_by(PriceObservation.observed_at.desc())
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

    # The manual button and the V2 scheduler both go through the same real
    # alert state machine - see app/monitoring.py, not duplicated here.
    return run_check_and_alert(trip_request, db)
