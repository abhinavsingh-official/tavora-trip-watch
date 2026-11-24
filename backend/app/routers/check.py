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
    """
    Read-only, no supplier calls. Loading the dashboard shouldn't burn a
    Sabre/Hotelbeds quota call - only "check price now" does that.
    """
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
    """
    Date validation happens inside run_check_and_alert before any supplier
    call - a 400 here comes from there, not this router.
    """

    """Manual button and the scheduler share this same alert logic, see app/monitoring.py."""
    return run_check_and_alert(trip_request, db)
