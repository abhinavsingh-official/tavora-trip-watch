import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, Notification, PriceObservation
from app.ownership import get_owned_booking, get_owned_notification
from app.schemas import BookingAttemptOut, BookingCreateIn
from app.sim_clock import sim_clock
from app.sim_controller import sim_controller

router = APIRouter(prefix="/api/requests", tags=["booking"])
bookings_router = APIRouter(prefix="/api/bookings", tags=["booking"])

# The order components are attempted in - also the order a compensating
# cancellation walks backwards through if a later one fails. Arbitrary but
# fixed, so "one piece books, then another fails" has a deterministic
# meaning (Sec. 09's chosen scenario).
BOOKING_ORDER = ("flight", "hotel", "cab")


def _fake_supplier_ref(component: str) -> str:
    return f"SIM-{component.upper()}-{uuid.uuid4().hex[:8]}"


def _build_booking(request_id: int, notification: Notification, accepted_total, db: Session) -> BookingAttempt:
    # V2's one real failure scenario: a forced failure on a specific
    # component (set via the Scenario Lab) stops booking at that point.
    # Everything confirmed *before* it gets a compensating cancellation -
    # the attempted undo, not a silent "it's fine." Anything after it was
    # never attempted at all, and stays "pending" rather than any outcome
    # we didn't actually observe.
    forced_failure_component = sim_controller.pop_booking_failure(request_id)

    statuses: dict[str, str] = {}
    refs: dict[str, str | None] = {}
    confirmed_before_failure: list[str] = []
    failed = False

    for component in BOOKING_ORDER:
        if component == forced_failure_component:
            statuses[component] = "failed"
            refs[component] = None
            failed = True
            break
        statuses[component] = "confirmed"
        refs[component] = _fake_supplier_ref(component)
        confirmed_before_failure.append(component)

    if failed:
        for component in confirmed_before_failure:
            # Attempted compensating cancellation - keep the original
            # supplier ref (that's what's actually being cancelled), just
            # change its status, rather than erasing what happened.
            statuses[component] = "cancelled"
        aggregate_status = "partial"
    else:
        aggregate_status = "confirmed"

    for component in BOOKING_ORDER:
        statuses.setdefault(component, "pending")
        refs.setdefault(component, None)

    return BookingAttempt(
        request_id=request_id,
        notification_id=notification.id,
        created_at=sim_clock.get_now(),
        accepted_total=accepted_total,
        flight_status=statuses["flight"],
        hotel_status=statuses["hotel"],
        cab_status=statuses["cab"],
        aggregate_status=aggregate_status,
        supplier_ref_flight=refs["flight"],
        supplier_ref_hotel=refs["hotel"],
        supplier_ref_cab=refs["cab"],
    )


@router.post("/{request_id}/book", response_model=BookingAttemptOut)
def book(request_id: int, user_id: int, payload: BookingCreateIn, db: Session = Depends(get_db)):
    # Ownership-checked (not just "does this notification belong to this
    # request_id", which said nothing about *whose* request it is).
    notification = get_owned_notification(payload.notification_id, user_id, db)
    if notification.request_id != request_id:
        raise HTTPException(status_code=404, detail="Notification not found for this request")

    # Idempotency guard: calling this twice for the same notification (a
    # double-click, a retried request, two open tabs) must not create a
    # second booking - return the existing one instead.
    existing = (
        db.query(BookingAttempt)
        .filter(BookingAttempt.notification_id == notification.id)
        .first()
    )
    if existing is not None:
        return existing

    # The real hold (Sec. 08): booking is only valid against a price that
    # was actually reviewed and is still within its 2-minute freeze. No
    # review yet, or an expired one, must not silently fall back to
    # whatever the latest price happens to be.
    if notification.held_observation_id is None or notification.held_until is None:
        raise HTTPException(
            status_code=400,
            detail="No active hold for this offer - review it again before booking.",
        )
    if sim_clock.get_now() > notification.held_until:
        raise HTTPException(
            status_code=409,
            detail="This hold has expired - review the offer again for a current price.",
        )

    held_observation = (
        db.query(PriceObservation)
        .filter(PriceObservation.id == notification.held_observation_id)
        .first()
    )
    if held_observation is None or held_observation.status != "complete" or held_observation.total_price is None:
        raise HTTPException(status_code=400, detail="No valid held price to book.")

    # The server derives the total from the held observation itself, not
    # from whatever the client sends - the held price is the single source
    # of truth for what's actually being booked.
    booking = _build_booking(request_id, notification, held_observation.total_price, db)
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        # Two near-simultaneous requests both passed the check above before
        # either committed - the unique constraint on notification_id is what
        # actually makes this atomic. Whoever lost the race gets the winner's
        # row back, not an error.
        db.rollback()
        winner = (
            db.query(BookingAttempt)
            .filter(BookingAttempt.notification_id == notification.id)
            .first()
        )
        if winner is not None:
            return winner
        raise
    db.refresh(booking)
    return booking


@bookings_router.get("/{booking_id}", response_model=BookingAttemptOut)
def get_booking(booking_id: int, user_id: int, db: Session = Depends(get_db)):
    # Lets BookingResult.tsx survive a page refresh instead of only working
    # when the booking was just created in the same browser session. Was
    # also missing ownership scoping until this pass - any user could read
    # any other user's booking by guessing an ID.
    return get_owned_booking(booking_id, user_id, db)
