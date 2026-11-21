from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, PriceObservation, TripRequest
from app.pricing import build_package
from app.schemas import PriceObservationOut
from app.sim_clock import sim_clock

router = APIRouter(prefix="/api/requests", tags=["check"])


def _create_observation(trip_request: TripRequest, db: Session) -> PriceObservation:
    package = build_package(trip_request)

    observation = PriceObservation(
        request_id=trip_request.id,
        observed_at=sim_clock.get_now(),
        flight_outbound_price=package.flight_outbound_price,
        flight_return_price=package.flight_return_price,
        flight_status=package.flight_status,
        hotel_total_price=package.hotel_total_price,
        hotel_status=package.hotel_status,
        cab_outbound_price=package.cab_outbound_price,
        cab_return_price=package.cab_return_price,
        cab_status=package.cab_status,
        taxes_fees=package.taxes_fees,
        total_price=package.total_price,
        status=package.status,
        raw_sources=package.raw_sources,
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


@router.post("/{request_id}/check", response_model=PriceObservationOut)
def check_price(request_id: int, db: Session = Depends(get_db)):
    trip_request = db.query(TripRequest).filter(TripRequest.id == request_id).first()
    if trip_request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    observation = _create_observation(trip_request, db)

    # V1's deliberately simple alert rule: at most one notification per
    # request, ever, on the first complete-and-under-budget observation.
    # The real first-crossing/5%-re-alert/above-budget-reset state machine
    # (Sec. 07) is V2's job (docs/versions/V1.md Sec. 8).
    already_notified = (
        db.query(Notification).filter(Notification.request_id == request_id).first()
        is not None
    )
    if (
        not already_notified
        and observation.status == "complete"
        and observation.total_price is not None
        and float(observation.total_price) <= float(trip_request.budget_inr)
    ):
        notification = Notification(
            request_id=request_id,
            observation_id=observation.id,
            created_at=sim_clock.get_now(),
        )
        db.add(notification)
        db.commit()

    return observation
