from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TripRequest
from app.ownership import get_owned_request
from app.schemas import TripRequestCreate, TripRequestOut

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.post("", response_model=TripRequestOut)
def create_request(payload: TripRequestCreate, db: Session = Depends(get_db)):
    trip_request = TripRequest(**payload.model_dump())
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)
    return trip_request


@router.get("", response_model=list[TripRequestOut])
def list_requests(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(TripRequest)
        .filter(TripRequest.user_id == user_id)
        .order_by(TripRequest.id)
        .all()
    )


@router.get("/{request_id}", response_model=TripRequestOut)
def get_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    return get_owned_request(request_id, user_id, db)
