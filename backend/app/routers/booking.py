import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, Notification, PriceObservation, SharedRoomPool
from app.monitoring import create_observation, expired_components, set_component_holds
from app.ownership import get_owned_booking, get_owned_notification, get_owned_request
from app.schemas import BookingAttemptOut, BookingCreateIn, BookingReconcileIn
from app.sim_clock import now_for_request
from app.sim_controller import sim_controller
from app.simulation_log import component_names_from_raw, log_event

router = APIRouter(prefix="/api/requests", tags=["booking"])
bookings_router = APIRouter(prefix="/api/bookings", tags=["booking"])

# Attempt order, and the order compensation walks backwards through on failure
BOOKING_ORDER = ("flight", "hotel", "cab")

_STATUS_FIELD = {"flight": "flight_status", "hotel": "hotel_status", "cab": "cab_status"}
_REF_FIELD = {
    "flight": "supplier_ref_flight",
    "hotel": "supplier_ref_hotel",
    "cab": "supplier_ref_cab",
}


def _fake_supplier_ref(component: str) -> str:
    return f"SIM-{component.upper()}-{uuid.uuid4().hex[:8]}"


def _component_status(booking: BookingAttempt, component: str) -> str:
    return getattr(booking, _STATUS_FIELD[component])


def _set_component(booking: BookingAttempt, component: str, status: str, ref: str | None = None) -> None:
    setattr(booking, _STATUS_FIELD[component], status)
    if ref is not None:  # cancellation calls this without a ref so the original ref stays intact
        setattr(booking, _REF_FIELD[component], ref)
    booking.updated_at = now_for_request(booking.request)  # every mutation stamps this for the Ops timeline


def _compensate(booking: BookingAttempt, component: str, request_id: int) -> None:
    # Cancellation can be forced to fail via the Lab, leaving "cancellation_failed" instead of a false "cancelled"
    if sim_controller.pop_cancel_failure(request_id) == component:
        _set_component(booking, component, "cancellation_failed")
    else:
        _set_component(booking, component, "cancelled")


def _try_claim_shared_room(request_id: int, db: Session) -> bool:
    # True unless in an exhausted pool; the UPDATE...WHERE rooms_remaining > 0 is atomic under concurrent claims
    pools = db.query(SharedRoomPool).all()
    matching = next((p for p in pools if request_id in (p.request_ids or [])), None)
    if matching is None:
        return True

    updated = (
        db.query(SharedRoomPool)
        .filter(SharedRoomPool.id == matching.id, SharedRoomPool.rooms_remaining > 0)
        .update(
            {SharedRoomPool.rooms_remaining: SharedRoomPool.rooms_remaining - 1},
            synchronize_session=False,
        )
    )
    db.commit()
    return updated > 0


def _aggregate_status(booking: BookingAttempt) -> str:
    statuses = [_component_status(booking, c) for c in BOOKING_ORDER]
    if any(s == "unknown" for s in statuses):
        return "needs_reconciliation"
    if any(s == "cancellation_failed" for s in statuses):
        return "manual_intervention"
    if all(s == "confirmed" for s in statuses):
        return "confirmed"
    if any(s in ("cancelled", "failed", "unavailable") for s in statuses):
        return "partial"
    return "in_progress"


def _run_booking_loop(
    booking: BookingAttempt,
    request_id: int,
    db: Session,
    forced: tuple[str, str] | None,
    restart_after: str | None,
) -> None:
    # Advances from the first pending component, never re-touching a resolved one; commits after each one so a restart is resumable
    confirmed_so_far = [c for c in BOOKING_ORDER if _component_status(booking, c) == "confirmed"]

    for component in BOOKING_ORDER:
        if _component_status(booking, component) != "pending":
            continue

        if forced is not None and forced[0] == component:
            forced_component, outcome = forced
            if outcome == "timeout":
                # Leaves it "unknown"; only /bookings/{id}/reconcile can move it forward from here
                _set_component(booking, component, "unknown")
                db.commit()
                return
            # fail/unavailable: stop and compensate everything already confirmed
            _set_component(booking, component, "failed" if outcome == "fail" else outcome)
            db.commit()
            for done in confirmed_so_far:
                _compensate(booking, done, request_id)
            db.commit()
            return

        if component == "hotel" and not _try_claim_shared_room(request_id, db):
            # treat an exhausted shared-room pool like a real "last room gone" failure
            _set_component(booking, component, "unavailable")
            db.commit()
            for done in confirmed_so_far:
                _compensate(booking, done, request_id)
            db.commit()
            return

        _set_component(booking, component, "confirmed", _fake_supplier_ref(component))
        confirmed_so_far.append(component)
        db.commit()

        if restart_after == component:
            # simulates the process dying here; a later book() call resumes from the next component
            return


def buy_now(request_id: int, user_id: int, db: Session) -> BookingAttempt:
    # Books the current best price immediately, regardless of budget - no need to open an alert first
    trip_request = get_owned_request(request_id, user_id, db)
    observation = create_observation(trip_request, db)

    now = now_for_request(trip_request)
    notification = Notification(
        request_id=trip_request.id,
        observation_id=observation.id,
        created_at=now,
    )
    if observation.status == "complete":
        notification.held_observation_id = observation.id
        set_component_holds(notification, now)
    db.add(notification)
    db.commit()
    db.refresh(notification)

    if notification.held_observation_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"This check came back '{observation.status}', not 'complete' - nothing to book.",
        )

    return book(trip_request.id, user_id, BookingCreateIn(notification_id=notification.id), db)


@router.post("/{request_id}/buy-now", response_model=BookingAttemptOut)
def buy_now_route(request_id: int, user_id: int, db: Session = Depends(get_db)):
    return buy_now(request_id, user_id, db)


@router.post("/{request_id}/book", response_model=BookingAttemptOut)
def book(request_id: int, user_id: int, payload: BookingCreateIn, db: Session = Depends(get_db)):
    """Checked ownership, not just that the notification belongs to this request_id."""
    notification = get_owned_notification(payload.notification_id, user_id, db)
    if notification.request_id != request_id:
        raise HTTPException(status_code=404, detail="Notification not found for this request")
    trip_request = get_owned_request(request_id, user_id, db)

    # idempotency guard: a double-click/retry on the same notification must not create a second booking row
    existing = (
        db.query(BookingAttempt)
        .filter(BookingAttempt.notification_id == notification.id)
        .first()
    )

    # blocks a new booking on a paused/cancelled request; an in-progress existing one is exempt and keeps resuming
    if trip_request.status != "active" and existing is None:
        raise HTTPException(
            status_code=400,
            detail=f"Request is {trip_request.status}, not active - this offer can no longer be booked.",
        )

    if existing is not None:
        if existing.aggregate_status == "in_progress":
            # resumes where the prior attempt stopped; never re-rolls a forced outcome
            _run_booking_loop(existing, request_id, db, forced=None, restart_after=None)
            existing.aggregate_status = _aggregate_status(existing)
            db.commit()
            db.refresh(existing)
            log_event(
                db,
                event_type="booking_attempt",
                trip_request=trip_request,
                summary=(
                    f"Resumed a stalled booking for {trip_request.user.name if trip_request.user else 'unknown user'}"
                    f" - now {existing.aggregate_status}"
                ),
                total_cost_inr=existing.accepted_total,
                status="finished" if existing.aggregate_status == "confirmed" else "unfinished",
            )
        # any other status is returned as-is; resolving it goes through reconcile(), not another attempt
        return existing

    # only valid against a reviewed price still within its hold window, never the latest price silently
    if notification.held_observation_id is None or notification.held_until_flight is None:
        raise HTTPException(
            status_code=400,
            detail="No active hold for this offer - review it again before booking.",
        )
    expired = expired_components(notification, now_for_request(trip_request))
    if expired:
        raise HTTPException(
            status_code=409,
            detail=f"The {' and '.join(expired)} hold has expired - review the offer again for a current price.",
        )

    held_observation = (
        db.query(PriceObservation)
        .filter(PriceObservation.id == notification.held_observation_id)
        .first()
    )
    if held_observation is None or held_observation.status != "complete" or held_observation.total_price is None:
        raise HTTPException(status_code=400, detail="No valid held price to book.")

    # Inserted fully "pending" as the state a restart resumes from; accepted_total is the held price, not the client's
    booking = BookingAttempt(
        request_id=request_id,
        notification_id=notification.id,
        created_at=now_for_request(trip_request),
        accepted_total=held_observation.total_price,
        flight_status="pending",
        hotel_status="pending",
        cab_status="pending",
        aggregate_status="in_progress",
    )
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        # two concurrent requests both passed the check; the unique constraint makes this atomic, loser gets the winner's row
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

    forced = sim_controller.pop_booking_failure(request_id)
    restart_after = sim_controller.pop_restart_after(request_id)
    _run_booking_loop(booking, request_id, db, forced=forced, restart_after=restart_after)
    booking.aggregate_status = _aggregate_status(booking)
    db.commit()
    db.refresh(booking)

    names = component_names_from_raw(held_observation.raw_sources)
    log_event(
        db,
        event_type="booking_attempt",
        trip_request=trip_request,
        summary=(
            f"Booking attempt for {trip_request.user.name if trip_request.user else 'unknown user'}"
            f" ({trip_request.origin} -> {trip_request.destination}): ₹{booking.accepted_total} - {booking.aggregate_status}"
        ),
        total_cost_inr=booking.accepted_total,
        is_simulated=True,
        status={
            "confirmed": "finished",
            "partial": "unfinished",
            "manual_intervention": "failed",
            "needs_reconciliation": "unfinished",
        }.get(booking.aggregate_status, "unfinished"),
        **names,
    )
    return booking


@bookings_router.get("/{booking_id}", response_model=BookingAttemptOut)
def get_booking(booking_id: int, user_id: int, db: Session = Depends(get_db)):
    """Lets BookingResult.tsx survive a page refresh instead of only working right after creation."""
    return get_owned_booking(booking_id, user_id, db)


@bookings_router.post("/{booking_id}/reconcile", response_model=BookingAttemptOut)
def reconcile(
    booking_id: int, user_id: int, payload: BookingReconcileIn, db: Session = Depends(get_db)
):
    """The only way a needs_reconciliation booking moves forward; book() refuses a second attempt instead of guessing."""
    booking = get_owned_booking(booking_id, user_id, db)
    if booking.aggregate_status != "needs_reconciliation":
        raise HTTPException(
            status_code=400, detail="This booking has no unresolved component to reconcile."
        )

    unknown = next((c for c in BOOKING_ORDER if _component_status(booking, c) == "unknown"), None)
    if unknown is None:
        raise HTTPException(status_code=400, detail="No unresolved component found.")

    confirmed_before = [
        c for c in BOOKING_ORDER[: BOOKING_ORDER.index(unknown)] if _component_status(booking, c) == "confirmed"
    ]

    if payload.outcome == "confirmed":
        # supplier did book it after all; resolve and continue with whatever came after
        _set_component(booking, unknown, "confirmed", _fake_supplier_ref(unknown))
        db.commit()
        _run_booking_loop(booking, booking.request_id, db, forced=None, restart_after=None)
    elif payload.outcome == "failed":
        # treat like a direct failure: compensate everything confirmed before it
        _set_component(booking, unknown, "failed")
        db.commit()
        for done in confirmed_before:
            _compensate(booking, done, booking.request_id)
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="outcome must be 'confirmed' or 'failed'")

    booking.aggregate_status = _aggregate_status(booking)
    db.commit()
    db.refresh(booking)

    log_event(
        db,
        event_type="reconcile",
        trip_request=booking.request,
        summary=(
            f"Reconciled an unresolved '{unknown}' component for "
            f"{booking.request.user.name if booking.request and booking.request.user else 'unknown user'}"
            f" as '{payload.outcome}' - now {booking.aggregate_status}"
        ),
        total_cost_inr=booking.accepted_total,
        status="finished" if booking.aggregate_status == "confirmed" else "unfinished",
    )
    return booking
