import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, Notification, PriceObservation
from app.ownership import get_owned_booking, get_owned_notification
from app.schemas import BookingAttemptOut, BookingCreateIn, BookingReconcileIn
from app.sim_clock import sim_clock
from app.sim_controller import sim_controller

router = APIRouter(prefix="/api/requests", tags=["booking"])
bookings_router = APIRouter(prefix="/api/bookings", tags=["booking"])

# The order components are attempted in - also the order a compensating
# cancellation walks backwards through if a later one fails. Arbitrary but
# fixed, so "one piece books, then another fails" has a deterministic
# meaning (Sec. 09's chosen scenario).
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
    # Only touches the supplier ref when one is actually given - a
    # compensating cancellation calls this without one, deliberately, so the
    # original ref (what's actually being cancelled) is never erased.
    if ref is not None:
        setattr(booking, _REF_FIELD[component], ref)


def _compensate(booking: BookingAttempt, component: str, request_id: int) -> None:
    """Attempt a compensating cancellation of an already-confirmed component.
    Sec. 09 row 6: the compensation itself can fail, injected one-shot via
    the Scenario Lab - the component stays "cancellation_failed" (visibly
    still confirmed-with-a-supplier, not falsely marked cancelled) so a
    human knows to check it, rather than the system claiming a rollback that
    didn't actually happen."""
    if sim_controller.pop_cancel_failure(request_id) == component:
        _set_component(booking, component, "cancellation_failed")
    else:
        _set_component(booking, component, "cancelled")


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
    """Advances booking through BOOKING_ORDER starting from the first still-
    "pending" component - never re-touches one that's already resolved.
    That's what makes this function double as both "book for the first
    time" and "resume after a simulated restart" (Sec. 09 row 5 / Sec. 11
    scenario 6): a resume call passes forced=None, restart_after=None (an
    already-decided outcome is never reconsidered), and the loop simply
    continues past whatever was already committed before the process
    "crashed."

    Commits after every single component, not once at the end - that
    per-component persistence is the actual resume mechanism, not just a
    performance detail.
    """
    confirmed_so_far = [c for c in BOOKING_ORDER if _component_status(booking, c) == "confirmed"]

    for component in BOOKING_ORDER:
        if _component_status(booking, component) != "pending":
            continue

        if forced is not None and forced[0] == component:
            forced_component, outcome = forced
            if outcome == "timeout":
                # Sec. 09 row 4: the supplier's response never resolves.
                # Leave this component "unknown" and stop - book() will
                # refuse to start a second attempt on this notification, and
                # only /bookings/{id}/reconcile can move it forward.
                _set_component(booking, component, "unknown")
                db.commit()
                return
            # "fail" or "unavailable" - stop here, compensate everything
            # already confirmed before it. "fail" maps to the "failed"
            # status value; "unavailable" is already its own status value
            # (reused from PriceObservation's vocabulary).
            _set_component(booking, component, "failed" if outcome == "fail" else outcome)
            db.commit()
            for done in confirmed_so_far:
                _compensate(booking, done, request_id)
            db.commit()
            return

        _set_component(booking, component, "confirmed", _fake_supplier_ref(component))
        confirmed_so_far.append(component)
        db.commit()

        if restart_after == component:
            # Sec. 09 row 5 / Sec. 11 scenario 6: simulate the process dying
            # right here. The row is already committed as "in_progress" with
            # this component confirmed - a later book() call on the same
            # notification resumes from the next one, never re-creates it.
            return


@router.post("/{request_id}/book", response_model=BookingAttemptOut)
def book(request_id: int, user_id: int, payload: BookingCreateIn, db: Session = Depends(get_db)):
    # Ownership-checked (not just "does this notification belong to this
    # request_id", which said nothing about *whose* request it is).
    notification = get_owned_notification(payload.notification_id, user_id, db)
    if notification.request_id != request_id:
        raise HTTPException(status_code=404, detail="Notification not found for this request")

    # Idempotency guard: calling this twice for the same notification (a
    # double-click, a retried request, two open tabs, or a genuine process
    # restart) must not create a second booking row.
    existing = (
        db.query(BookingAttempt)
        .filter(BookingAttempt.notification_id == notification.id)
        .first()
    )
    if existing is not None:
        if existing.aggregate_status == "in_progress":
            # Resume exactly where a prior attempt stopped - never re-rolls
            # a forced outcome, only continues from the first still-pending
            # component (Sec. 09 row 5).
            _run_booking_loop(existing, request_id, db, forced=None, restart_after=None)
            existing.aggregate_status = _aggregate_status(existing)
            db.commit()
            db.refresh(existing)
        # Any other existing status (confirmed/partial/needs_reconciliation/
        # manual_intervention) is returned as-is - resolving an unresolved
        # outcome happens through reconcile(), never by creating another
        # attempt (Sec. 09 row 4).
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

    # Inserted immediately, fully "pending", before any component is
    # attempted - this is the persisted state a restart resumes from (Sec.
    # 09 row 5), not something reconstructed after the fact.
    booking = BookingAttempt(
        request_id=request_id,
        notification_id=notification.id,
        created_at=sim_clock.get_now(),
        # The server derives the total from the held observation itself, not
        # from whatever the client sends - the held price is the single
        # source of truth for what's actually being booked.
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

    forced = sim_controller.pop_booking_failure(request_id)
    restart_after = sim_controller.pop_restart_after(request_id)
    _run_booking_loop(booking, request_id, db, forced=forced, restart_after=restart_after)
    booking.aggregate_status = _aggregate_status(booking)
    db.commit()
    db.refresh(booking)
    return booking


@bookings_router.get("/{booking_id}", response_model=BookingAttemptOut)
def get_booking(booking_id: int, user_id: int, db: Session = Depends(get_db)):
    # Lets BookingResult.tsx survive a page refresh instead of only working
    # when the booking was just created in the same browser session. Was
    # also missing ownership scoping until this pass - any user could read
    # any other user's booking by guessing an ID.
    return get_owned_booking(booking_id, user_id, db)


@bookings_router.post("/{booking_id}/reconcile", response_model=BookingAttemptOut)
def reconcile(
    booking_id: int, user_id: int, payload: BookingReconcileIn, db: Session = Depends(get_db)
):
    """Resolves a component left "unknown" after a simulated supplier
    timeout (Sec. 09 row 4). This is the only way a `needs_reconciliation`
    booking ever moves forward - book() deliberately refuses to start a
    second attempt instead of guessing."""
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
        # The supplier did book it after all - resolve it, then continue
        # booking whatever came after it, which was never attempted while
        # the outcome was unknown.
        _set_component(booking, unknown, "confirmed", _fake_supplier_ref(unknown))
        db.commit()
        _run_booking_loop(booking, booking.request_id, db, forced=None, restart_after=None)
    elif payload.outcome == "failed":
        # It never actually booked - treat it exactly like a direct failure
        # at this point: compensate everything confirmed before it, leave
        # anything after it untouched (never attempted, stays "pending").
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
    return booking
